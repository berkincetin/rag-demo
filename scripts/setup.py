"""Prepare the local environment: check Ollama, pull the chat model.

Ollama itself is never installed automatically — an OS-level install is the
user's decision, so this prints the command and stops.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.config import Config  # noqa: E402
from src.rag.ollama_admin import OllamaAdmin, OllamaUnavailable  # noqa: E402

_INSTALL_HINT = {
    "win32": "Ollama kurulu değil. https://ollama.com/download adresinden Windows "
    "kurulumunu indirip çalıştırın (veya: winget install Ollama.Ollama).",
    "darwin": "Ollama kurulu değil. https://ollama.com/download veya: brew install ollama",
    "linux": "Ollama kurulu değil. https://ollama.com/download veya: "
    "curl -fsSL https://ollama.com/install.sh | sh",
}


_QUANT_SUFFIX = re.compile(r"-q\d+[_\w]*$", re.IGNORECASE)


def _same_model(left: str, right: str) -> bool:
    """Compare model tags ignoring the quantisation suffix."""
    return _QUANT_SUFFIX.sub("", left) == _QUANT_SUFFIX.sub("", right)


@dataclass(frozen=True)
class SetupPlan:
    action: str  # "instruct" | "pull" | "ok"
    message: str
    model: str | None = None


def plan_setup(
    ollama_running: bool, installed_models: list[str], platform: str, model: str | None = None
) -> SetupPlan:
    """Decide what setup step is needed, without performing it."""
    model = model or Config.load().llm_model

    if not ollama_running:
        hint = _INSTALL_HINT.get(platform, _INSTALL_HINT["linux"])
        return SetupPlan("instruct", f"{hint}\nKurduktan sonra bu betiği tekrar çalıştırın.")

    # A quantised build (…-q4_K_M) and its plain tag are the same weights, so
    # either one satisfies the other. Comparing raw strings would re-download
    # several gigabytes for nothing.
    if any(_same_model(name, model) for name in installed_models):
        return SetupPlan("ok", f"Hazır: {model} zaten yüklü.", model)

    return SetupPlan("pull", f"{model} indirilecek (birkaç GB sürebilir).", model)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    admin = OllamaAdmin()

    try:
        installed = [entry.name for entry in admin.list_local()]
        running = True
    except OllamaUnavailable:
        installed, running = [], False

    plan = plan_setup(running, installed, sys.platform)
    print(plan.message)

    if plan.action == "instruct":
        return 1
    if plan.action == "pull":
        print("İndiriliyor…")
        admin.pull(plan.model, on_progress=lambda p: print(f"  {p.status}", end="\r"))
        print("\nTamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
