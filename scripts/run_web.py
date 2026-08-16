"""Start the API and the Next.js front-end with one command.

The case asks for a three-command start. Without this the Next.js path would
need four or five (`pip install`, `ingest`, `npm install`, `uvicorn`, `npm run
dev`), so the launcher folds the last three into one:

    pip install -r requirements.txt
    python scripts/ingest.py
    python scripts/run_web.py        # API + arayüz

Ctrl+C stops both. Use `--prod` to serve a production build instead of the dev
server.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def api_command(port: int) -> list[str]:
    """Uvicorn invocation for the HTTP API."""
    return ["uvicorn", "src.rag.api:app", "--host", "0.0.0.0", "--port", str(port)]


def web_command(dev: bool) -> list[str]:
    """Dev server while iterating; the built server for a production run."""
    return ["npm", "run", "dev"] if dev else ["npm", "start"]


def needs_npm_install(web_dir: Path) -> bool:
    """True when dependencies have never been installed in `web_dir`."""
    return not (web_dir / "node_modules").exists()


def _require_npm() -> str:
    npm = shutil.which("npm")
    if npm is None:
        sys.exit(
            "npm bulunamadı. Next.js arayüzü için Node.js 18+ gerekiyor "
            "(https://nodejs.org). Gradio arayüzü Node gerektirmez: "
            "python gradio_app.py"
        )
    return npm


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="API + Next.js arayüzünü başlat")
    parser.add_argument("--port", type=int, default=8000, help="API portu")
    parser.add_argument("--prod", action="store_true", help="Üretim derlemesini sun")
    args = parser.parse_args(argv)

    npm = _require_npm()

    if needs_npm_install(WEB_DIR):
        print("→ npm install (ilk çalıştırma, birkaç dakika sürebilir)…")
        subprocess.run([npm, "install"], cwd=WEB_DIR, check=True)

    if args.prod:
        print("→ npm run build…")
        subprocess.run([npm, "run", "build"], cwd=WEB_DIR, check=True)

    print(f"→ API      http://localhost:{args.port}")
    api = subprocess.Popen(api_command(args.port))
    # A moment's head start so the first page load does not race the API and
    # flash the "API'ye ulaşılamıyor" banner.
    time.sleep(2)

    print("→ Arayüz   http://localhost:3000")
    command = web_command(dev=not args.prod)
    web = subprocess.Popen([npm, *command[1:]], cwd=WEB_DIR)

    print("\nDurdurmak için Ctrl+C.\n")
    try:
        while True:
            # If either side dies, stop the other rather than leaving half a
            # stack running and a port held.
            if api.poll() is not None or web.poll() is not None:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in (web, api):
            if process.poll() is None:
                process.terminate()
        for process in (web, api):
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
