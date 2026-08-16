"""Prove the notebook's inlined functions behave identically to src/analysis/.

Executes the notebook's function-definition cells in a fresh namespace, then
runs both implementations over the real workbook and compares the outputs.
A divergence here would mean the deliverable reports different numbers.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

nb = json.loads((ROOT / "notebooks" / "analiz_full.ipynb").read_text(encoding="utf-8"))

# Build the notebook namespace: the imports cell plus the five inlined modules.
namespace = {
    "DATA_PATH": ROOT / "AI Engineer" / "bolum2_veriseti.xlsx",
    "FIGURE_DIR": Path("figures"),
    "Path": Path,
}
executed = 0
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = "".join(cell["source"])
    if "%pip" in src or "_CANDIDATES" in src:
        continue
    # Stop once the analysis proper begins.
    if "load_raw()" in src and "def load_raw" not in src:
        break
    exec(compile(src, f"<cell{executed}>", "exec"), namespace)
    executed += 1

print(f"notebook: {executed} tanım hücresi çalıştırıldı\n")

# --- reference implementation ------------------------------------------------
# Imported after the notebook cells ran, so the two namespaces stay separate and
# a name defined by the notebook can never satisfy a reference lookup.
# ruff: noqa: E402
from src.analysis.clean import clean as m_clean
from src.analysis.forecast import lgbm_walk_forward as m_lgbm
from src.analysis.forecast import ma3 as m_ma3
from src.analysis.forecast import metrics_by_market as m_mbm
from src.analysis.forecast import naive as m_naive
from src.analysis.forecast import snaive as m_snaive
from src.analysis.forecast import walk_forward as m_wf
from src.analysis.load import load_raw as m_load
from src.analysis.metrics import derived_metrics as m_derived
from src.analysis.metrics import hhi as m_hhi
from src.analysis.metrics import market_share as m_share
from src.analysis.metrics import promo_revenue_loss as m_promo
from src.analysis.metrics import seasonal_index as m_sidx
from src.analysis.metrics import seasonality_strength as m_sstr
from src.analysis.metrics import yoy_growth as m_yoy

failures = []


def check(label, a, b):
    try:
        if isinstance(a, pd.DataFrame):
            pd.testing.assert_frame_equal(a, b, check_dtype=False, check_categorical=False)
        elif isinstance(a, pd.Series):
            pd.testing.assert_series_equal(a, b, check_dtype=False, check_categorical=False)
        elif a is None or b is None:
            assert a is None and b is None, f"{a!r} != {b!r}"
        elif isinstance(a, float):
            assert abs(a - b) < 1e-9, f"{a} != {b}"
        else:
            assert a == b, f"{a!r} != {b!r}"
        print(f"  OK    {label}")
    except AssertionError as exc:
        failures.append(label)
        print(f"  FARK  {label}: {str(exc)[:200]}")


print("=== yükleme ve temizleme ===")
nb_raw = namespace["load_raw"]()
md_raw = m_load()
check("load_raw", nb_raw, md_raw)

nb_clean, nb_report = namespace["clean"](nb_raw)
md_clean, md_report = m_clean(md_raw)
check("clean (çerçeve)", nb_clean, md_clean)
check("clean rapor: raw_rows", nb_report.raw_rows, md_report.raw_rows)
check("clean rapor: clean_rows", nb_report.clean_rows, md_report.clean_rows)
check("clean rapor: rescaled_markets", nb_report.rescaled_markets, md_report.rescaled_markets)
check("clean rapor: mf_clipped", nb_report.mf_clipped, md_report.mf_clipped)
check("clean rapor: return_rows", nb_report.return_rows, md_report.return_rows)
check("clean rapor: pre_launch", nb_report.pre_launch_dropped, md_report.pre_launch_dropped)
check("clean rapor: short_series", nb_report.short_series, md_report.short_series)

print("\n=== türetilmiş metrikler ===")
nb_df = namespace["derived_metrics"](nb_clean)
md_df = m_derived(md_clean)
check("derived_metrics", nb_df, md_df)
check("market_share", namespace["market_share"](nb_df), m_share(md_df))
check("hhi", namespace["hhi"](nb_df), m_hhi(md_df))
check("yoy_growth", namespace["yoy_growth"](nb_df), m_yoy(md_df))
check("promo_revenue_loss", namespace["promo_revenue_loss"](nb_df), m_promo(md_df))

print("\n=== mevsimsellik (STL) ===")
one = nb_df[nb_df.sirket == "Şirket 1"]
for (mkt, prod), g in list(one.groupby(["pazar", "urun"], observed=True))[:6]:
    s = g.sort_values("tarih").set_index("tarih").brut_kutu.astype(float)
    check(f"seasonality_strength {mkt}/{prod}", namespace["seasonality_strength"](s), m_sstr(s))
    check(f"seasonal_index {mkt}/{prod}", namespace["seasonal_index"](s), m_sidx(s))

print("\n=== tahmin modelleri ===")
md_one = md_df[md_df.sirket == "Şirket 1"]
for name, nb_fn, md_fn in [
    ("naive", namespace["naive"], m_naive),
    ("snaive", namespace["snaive"], m_snaive),
    ("ma3", namespace["ma3"], m_ma3),
]:
    check(f"walk_forward {name}", namespace["walk_forward"](one, nb_fn), m_wf(md_one, md_fn))

check("lgbm_walk_forward (MF ile)", namespace["lgbm_walk_forward"](one, True), m_lgbm(md_one, True))
check(
    "lgbm_walk_forward (MF siz)", namespace["lgbm_walk_forward"](one, False), m_lgbm(md_one, False)
)
check(
    "metrics_by_market",
    namespace["metrics_by_market"](namespace["walk_forward"](one, namespace["naive"])),
    m_mbm(m_wf(md_one, m_naive)),
)

print("\n" + "=" * 70)
if failures:
    print(f"BASARISIZ — {len(failures)} fark: {failures}")
    raise SystemExit(1)
print("TUM KONTROLLER GECTI — notebook fonksiyonlari modullerle birebir ayni")
