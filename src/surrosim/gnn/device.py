"""Device selection for torch models with a CPU fallback.

Some environments expose a CUDA device that fails at the first allocation
(broken driver, no free memory, unsupported runtime). A surrogate pipeline
must not fail for that: ``resolve_device`` verifies the device with a tiny
allocation and falls back to CPU. ``SURROSIM_DEVICE=cpu|cuda`` overrides.
"""

import os

import torch


def resolve_device() -> torch.device:
    override = os.environ.get("SURROSIM_DEVICE")
    if override:
        return torch.device(override)
    if torch.cuda.is_available():
        try:
            torch.cuda.init()
            free, _total = torch.cuda.mem_get_info()
            if free < 1.0 * 1024**3:
                return torch.device("cpu")
            torch.zeros(1, device="cuda")
            return torch.device("cuda")
        except Exception:  # noqa: BLE001 - any CUDA failure means use CPU
            return torch.device("cpu")
    return torch.device("cpu")
