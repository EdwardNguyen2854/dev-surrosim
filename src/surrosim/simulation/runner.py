"""CalculiX process runner with machine-readable failure states."""

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
import subprocess
import time


@dataclass(frozen=True)
class SolverRun:
    status: str
    success: bool
    return_code: int | None
    runtime_seconds: float
    executable: str
    job_name: str
    stdout: str
    stderr: str
    output_files: tuple[str, ...]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["output_files"] = list(self.output_files)
        return data


class CalculixRunner:
    def __init__(self, executable: str = "ccx") -> None:
        self.executable = executable

    def _resolve(self) -> str | None:
        candidate = Path(self.executable)
        if candidate.parent != Path(".") or candidate.is_absolute():
            return str(candidate) if candidate.exists() else None
        return shutil.which(self.executable)

    def run(self, input_file: str | Path, timeout_seconds: float = 300.0) -> SolverRun:
        deck = Path(input_file).resolve()
        if not deck.exists():
            raise ValueError(f"CalculiX input deck not found: {deck}")
        if deck.suffix.lower() != ".inp":
            raise ValueError("CalculiX input deck must use the .inp suffix")
        resolved = self._resolve()
        job_name = deck.stem
        if resolved is None:
            return SolverRun(
                status="SOLVER_NOT_FOUND", success=False, return_code=None,
                runtime_seconds=0.0, executable=self.executable, job_name=job_name,
                stdout="", stderr=f"CalculiX executable not found: {self.executable}",
                output_files=(),
            )

        start = time.perf_counter()
        try:
            completed = subprocess.run(
                [resolved, job_name], cwd=deck.parent, capture_output=True,
                text=True, timeout=timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            runtime = time.perf_counter() - start
            return SolverRun(
                status="SOLVER_TIMEOUT", success=False, return_code=None,
                runtime_seconds=runtime, executable=resolved, job_name=job_name,
                stdout=exc.stdout or "", stderr=exc.stderr or "", output_files=(),
            )
        runtime = time.perf_counter() - start
        suffixes = (".frd", ".dat", ".sta", ".cvg")
        outputs = tuple(
            str(deck.with_suffix(suffix).name)
            for suffix in suffixes
            if deck.with_suffix(suffix).exists()
        )
        has_frd = deck.with_suffix(".frd").exists()
        success = completed.returncode == 0 and has_frd
        if completed.returncode != 0:
            status = "SOLVER_FAILED"
        elif not has_frd:
            status = "OUTPUT_MISSING"
        else:
            status = "SUCCESS"
        return SolverRun(
            status=status, success=success, return_code=completed.returncode,
            runtime_seconds=runtime, executable=resolved, job_name=job_name,
            stdout=completed.stdout, stderr=completed.stderr, output_files=outputs,
        )
