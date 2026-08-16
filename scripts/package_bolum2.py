"""Build bolum2-analiz.zip — the Part 2 deliverable.

    python scripts/package_bolum2.py

Runs `notebooks/analiz_full.ipynb` in a scratch directory (so the repo is not
polluted with a re-executed notebook and a stray figures/ folder), then ships
the executed copy together with the PNGs it produced, the source workbook, a
README and a requirements file.

The notebook is executed rather than shipped as-is on purpose: the evaluator
gets a file whose outputs and charts are already visible, and running it here
proves the delivered notebook actually works.
"""

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "analiz_full.ipynb"
WORKBOOK = ROOT / "AI Engineer" / "bolum2_veriseti.xlsx"
README = ROOT / "docs" / "bolum2-teslim-README.md"
OUT = ROOT / "bolum2-analiz.zip"

REQUIREMENTS = """\
# Bölüm 2 — Satış ve talep analizi bağımlılıkları.
# Sürümler kurulu ortamdan (`pip freeze`) birebir alındı, tahmin edilmedi.
# Not: analiz_full.ipynb ilk hücresinde bunları kendisi de kurar.

pandas==2.2.3
numpy==2.2.6
openpyxl==3.1.5
matplotlib==3.10.9
statsmodels==0.14.6
scipy==1.15.3
scikit-learn==1.7.2
lightgbm==4.7.0
jupyter==1.1.1
"""


def _execute(workdir: Path) -> Path:
    """Run the notebook in `workdir` and return the executed copy."""
    target = workdir / NOTEBOOK.name
    shutil.copy2(NOTEBOOK, target)
    shutil.copy2(WORKBOOK, workdir / WORKBOOK.name)

    print("→ notebook çalıştırılıyor (~2 dk)…")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--inplace",
            "--ExecutePreprocessor.timeout=1800",
            target.name,
        ],
        cwd=workdir,
        check=True,
    )
    return target


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    for required in (NOTEBOOK, WORKBOOK, README):
        if not required.exists():
            raise SystemExit(f"eksik girdi: {required}")

    with tempfile.TemporaryDirectory(prefix="bolum2-") as scratch:
        workdir = Path(scratch)
        executed = _execute(workdir)
        figures = sorted((workdir / "figures").glob("*.png"))
        if not figures:
            raise SystemExit("notebook hiç figür üretmedi — paketleme durduruldu")

        if OUT.exists():
            OUT.unlink()

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(executed, "analiz_full.ipynb")
            zf.write(WORKBOOK, "bolum2_veriseti.xlsx")
            zf.write(README, "README.md")
            zf.writestr("requirements.txt", REQUIREMENTS)
            for png in figures:
                zf.write(png, f"figures/{png.name}")

        print(f"\n{4 + len(figures)} dosya · {len(figures)} figür")

    print(f"zip: {OUT.name} ({OUT.stat().st_size / 1_048_576:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
