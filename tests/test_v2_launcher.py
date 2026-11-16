import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
from types import SimpleNamespace

import pytest

from surrosim.plate import Plate


SPEC = importlib.util.spec_from_file_location(
    "v2_launcher", Path(__file__).resolve().parents[1] / "tools/run_v2.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def test_lock_excludes_another_process_and_releases(tmp_path):
    lock = tmp_path / "launcher.lock"
    code = (
        "import runpy; from pathlib import Path; "
        f"m = runpy.run_path({str(Path(launcher.__file__))!r}); "
        f"ctx = m['instance_lock'](Path({str(lock)!r})); "
        "ctx.__enter__(); ctx.__exit__(None, None, None)"
    )
    with launcher.instance_lock(lock):
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert result.returncode != 0
        assert "already running" in result.stderr
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("memory_pressure", [False, True])
def test_failed_batch_stops_before_training_and_records_failure(tmp_path, monkeypatch, memory_pressure):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    base = data / "dataset_v1"
    base.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    row = {"case_id": "example", "split": "train", "tag": "", **Plate().as_dict()}
    launcher.write_table(data / "designs_v2.csv", [row], list(row))
    launcher.write_table(base / "dataset.csv", [], list(row))
    calls = []

    def failed_command(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["OMP_NUM_THREADS"] == "1"
        if memory_pressure and len(calls) == 1:
            raise launcher.MemoryPressure("test low RAM")
        return SimpleNamespace(returncode=2)

    monkeypatch.setattr(launcher.subprocess, "run", failed_command)
    monkeypatch.setattr(launcher, "run_fea", failed_command)
    with pytest.raises(RuntimeError, match="exit code 2"):
        launcher.run_pipeline(SimpleNamespace(chunk_size=20, timeout=600, ccx="ccx", jobs=2), state)
    assert len(calls) == (2 if memory_pressure else 1)
    assert calls[0][3:5] == ["dataset", "run"]
    assert calls[0][calls[0].index("--jobs") + 1] == "2"
    if memory_pressure:
        assert calls[1][calls[1].index("--jobs") + 1] == "1"
    status = json.loads((state / "status.json").read_text())
    assert status["stage"] == "failed"
    assert "exit code 2" in status["error"]


@pytest.mark.parametrize("gate_passes", [True, False])
def test_scalar_overlap_requires_gated_labels(tmp_path, monkeypatch, gate_passes):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    base = data / "dataset_v1"
    base.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    row = {"case_id": "example", "split": "train", "tag": "", **Plate().as_dict()}
    launcher.write_table(data / "designs_v2.csv", [row], list(row))
    launcher.write_table(base / "dataset.csv", [], list(row))
    scalar_started = threading.Event()
    graph_started = threading.Event()
    scalar_finished = threading.Event()
    calls = []

    def execute(command, **kwargs):
        args = command[3:]
        calls.append(args[:2])
        if args[:2] == ["dataset", "build"]:
            out = data / "dataset_v2"
            out.mkdir()
            (out / "manifest.json").write_text(json.dumps({
                "cases_failed": 0 if gate_passes else 1,
                "cases_in_dataset": 1 if gate_passes else 0,
            }))
        elif args[:2] == ["train", "scalar"]:
            assert kwargs["env"]["LOKY_MAX_CPU_COUNT"] == "2"
            assert kwargs["env"]["OMP_THREAD_LIMIT"] == "2"
            scalar_started.set()
            assert graph_started.wait(5), "Graph FEA did not overlap scalar training"
            scalar_finished.set()
        elif args[:2] == ["dataset", "run"] and "graph" in args:
            assert scalar_started.wait(5)
            assert args[args.index("--jobs") + 1] == "1"
            graph_started.set()
        elif args[:2] == ["graph", "export"]:
            out = data / "graphs_v2"
            out.mkdir()
            (out / "manifest.json").write_text('{"skipped": 0, "graphs": 1}')
        elif args[:2] == ["train", "gnn"]:
            assert scalar_finished.is_set()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher.subprocess, "run", execute)
    monkeypatch.setattr(launcher, "run_fea", execute)
    args = SimpleNamespace(chunk_size=20, timeout=600, ccx="ccx", jobs=2)
    if gate_passes:
        launcher.run_pipeline(args, state)
        assert scalar_finished.is_set()
        assert json.loads((state / "status.json").read_text())["stage"] == "awaiting_model_review"
    else:
        with pytest.raises(RuntimeError, match="incomplete after gating"):
            launcher.run_pipeline(args, state)
        assert not scalar_started.is_set()
        assert ["graph", "export"] not in calls
        assert ["train", "gnn"] not in calls


def test_memory_monitor_stops_its_process_tree(tmp_path, monkeypatch):
    killed = []
    child = SimpleNamespace(kill=lambda: killed.append("worker"))
    parent = SimpleNamespace(
        children=lambda recursive: [child], kill=lambda: killed.append("batch"),
    )
    process = SimpleNamespace(pid=123, poll=lambda: None, wait=lambda: 1)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(launcher.psutil, "virtual_memory", lambda: SimpleNamespace(available=3 * 1024**3))
    monkeypatch.setattr(launcher.psutil, "Process", lambda pid: parent)
    monkeypatch.setattr(launcher.psutil, "wait_procs", lambda *a, **kw: None)
    with pytest.raises(launcher.MemoryPressure):
        launcher.run_fea(["fake"], cwd=tmp_path, env={})
    assert killed == ["batch", "worker"]
