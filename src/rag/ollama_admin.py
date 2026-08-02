"""Manage locally installed Ollama models from the UI.

The HTTP layer is injectable so the tests never touch the network. Progress is
reported as a fraction only when Ollama actually sends a total — an invented
percentage would be worse than no percentage.
"""

import json as jsonlib
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import requests

_DEFAULT_PULL_TIMEOUT = 3600


class OllamaUnavailable(RuntimeError):
    """Ollama could not be reached."""


@dataclass(frozen=True)
class LocalModel:
    name: str
    size_bytes: int | None = None


@dataclass(frozen=True)
class PullProgress:
    status: str
    completed: int | None = None
    total: int | None = None

    @property
    def fraction(self) -> float | None:
        if not self.total or self.completed is None:
            return None
        return self.completed / self.total


class _RequestsHttp:
    def get_json(self, url: str, timeout: int) -> dict[str, Any]:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def post_stream(self, url: str, json: dict[str, Any], timeout: int) -> Iterator[dict]:
        with requests.post(url, json=json, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    yield jsonlib.loads(line)

    def delete(self, url: str, json: dict[str, Any], timeout: int) -> None:
        response = requests.delete(url, json=json, timeout=timeout)
        response.raise_for_status()


class OllamaAdmin:
    def __init__(self, base_url: str | None = None, http: Any = None) -> None:
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._http = http or _RequestsHttp()
        self.pull_timeout = int(os.getenv("OLLAMA_PULL_TIMEOUT", str(_DEFAULT_PULL_TIMEOUT)))

    def list_local(self) -> list[LocalModel]:
        try:
            payload = self._http.get_json(f"{self.base_url}/api/tags", timeout=15)
        except Exception as error:  # noqa: BLE001 - any transport failure means unavailable
            raise OllamaUnavailable(
                f"Ollama'ya ulaşılamadı ({self.base_url}). Çalıştığından emin olun."
            ) from error
        return [
            LocalModel(name=entry["name"], size_bytes=entry.get("size"))
            for entry in payload.get("models", [])
        ]

    def is_available(self) -> bool:
        try:
            self.list_local()
        except OllamaUnavailable:
            return False
        return True

    def pull(self, model: str, on_progress: Callable[[PullProgress], None] | None = None) -> None:
        try:
            lines = self._http.post_stream(
                f"{self.base_url}/api/pull", json={"model": model}, timeout=self.pull_timeout
            )
            for line in lines:
                status = line.get("status", "")
                if status == "success":
                    continue
                if on_progress is not None:
                    on_progress(
                        PullProgress(
                            status=status,
                            completed=line.get("completed"),
                            total=line.get("total"),
                        )
                    )
        except OllamaUnavailable:
            raise
        except Exception as error:  # noqa: BLE001
            raise OllamaUnavailable(f"'{model}' indirilemedi: {error}") from error

    def delete(self, model: str) -> None:
        try:
            self._http.delete(f"{self.base_url}/api/delete", json={"model": model}, timeout=60)
        except Exception as error:  # noqa: BLE001
            raise OllamaUnavailable(f"'{model}' silinemedi: {error}") from error
