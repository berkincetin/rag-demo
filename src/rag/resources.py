"""Measure what a local model actually costs in machine resources.

Cloud models bill in tokens; local models bill in your CPU, RAM and GPU. Those
are the only figures that make a local-vs-cloud comparison honest, so they are
sampled while the agent runs and stored next to the token counts.

Everything that cannot be measured stays `None`. In particular a missing GPU
reading is `None`, while a model loaded with `size_vram == 0` is a real
measurement meaning "loaded, but running on the CPU" — collapsing the two into
0 would erase the distinction.
"""

import os
import threading
from dataclasses import dataclass
from typing import Any

import psutil
import requests


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_percent: float | None = None
    ram_used_mb: int = 0
    ram_total_mb: int = 0
    gpu_used_mb: int | None = None


class _RequestsHttp:
    def get_json(self, url: str, timeout: int) -> dict[str, Any]:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()


def read_gpu_vram_mb(http: Any = None, base_url: str | None = None) -> int | None:
    """VRAM the currently loaded Ollama model occupies, in MB.

    `None` when nothing could be read (Ollama down, or no model loaded);
    `0` when a model is loaded but running on the CPU.
    """
    http = http or _RequestsHttp()
    base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        # Short timeout: this is a nice-to-have measurement, never worth
        # delaying an answer for.
        payload = http.get_json(f"{base_url}/api/ps", timeout=2)
    except Exception:  # noqa: BLE001 - any failure means "not measurable"
        return None

    models = payload.get("models") or []
    if not models:
        return None

    vram = models[0].get("size_vram")
    return None if vram is None else int(vram) // (1024 * 1024)


class ResourceMonitor:
    """Samples system resources on a background thread and keeps the peaks.

    Peaks, not averages: a model that pins the CPU for ten seconds inside a
    six-minute call has an unremarkable average and a very informative peak.
    """

    def __init__(self, interval: float = 1.0, read_gpu: bool = True) -> None:
        self.interval = interval
        # Cloud models consume no local GPU, so asking Ollama about VRAM would
        # both mislead and cost a round trip.
        self.read_gpu = read_gpu
        self.peak_cpu_percent: float | None = None
        self.peak_ram_mb: int | None = None
        self.gpu_vram_mb: int | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def sample(self) -> ResourceSnapshot:
        memory = psutil.virtual_memory()
        return ResourceSnapshot(
            cpu_percent=psutil.cpu_percent(interval=None),
            ram_used_mb=int(memory.used / (1024 * 1024)),
            ram_total_mb=int(memory.total / (1024 * 1024)),
        )

    def _record(self, snapshot: ResourceSnapshot) -> None:
        if snapshot.cpu_percent is not None:
            self.peak_cpu_percent = max(self.peak_cpu_percent or 0.0, snapshot.cpu_percent)
        self.peak_ram_mb = max(self.peak_ram_mb or 0, snapshot.ram_used_mb)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._record(self.sample())

    def start(self) -> None:
        psutil.cpu_percent(interval=None)  # prime the counter; the first read is meaningless
        self._record(self.sample())
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        if self.read_gpu:
            self.gpu_vram_mb = read_gpu_vram_mb()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def __enter__(self) -> "ResourceMonitor":
        self.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.stop()


class NullMonitor:
    """Measures nothing, reports nothing — used when no store will read it."""

    peak_cpu_percent: float | None = None
    peak_ram_mb: int | None = None
    gpu_vram_mb: int | None = None

    def __enter__(self) -> "NullMonitor":
        return self

    def __exit__(self, *_exc) -> None:
        return None
