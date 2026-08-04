# Task 4: Grafik stili ve figür yazıcı

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §6.
> **Önceki:** [Task 3](03-metrikler.md) · **Sonraki:** [Task 5](05-tahmin-temel.md)

**Dosyalar:** `src/analysis/plots.py` · **Test:** `tests/test_analysis_plots.py`

## Interfaces

```python
MARKET_COLORS: dict[str, str]     # A/B/C/D sabit palet
COMPANY_COLORS: dict[str, str]    # Şirket 1 vurgulu, diğerleri nötr
FIGURE_DIR = Path("figures")

def apply_style() -> None                       # rcParams, TR sayı biçimi
def tr_number(x: float, decimals: int = 0) -> str  # 1234.5 → '1.234,5'
def save_figure(fig, name: str) -> Path                # figures/<name>.png, 150 dpi
```

---

- [ ] **Adım 1: Kırmızı testler**

| Test | Doğruladığı |
|---|---|
| `test_tr_sayi_binlik_nokta_ondalik_virgul` | `1234567.8` → `'1.234.567,8'` |
| `test_tr_sayi_negatif_ve_sifir` | Sınır durumları |
| `test_dort_pazarin_da_rengi_tanimli` | Palet eksiksiz — grafik ortasında `KeyError` olmasın |
| `test_kaydet_png_uretiyor_ve_yol_donduruyor` | `tmp_path` altında dosya var ve > 0 bayt |
| `test_stil_uygula_matplotlib_backend_ini_bozmuyor` | Agg backend'te çalışıyor (notebook dışı test) |

⚠️ Testler `matplotlib.use("Agg")` ile başlar — headless ortamda pencere açılmasın.

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `plots.py` yaz.** Tüm başlık/eksen/lejant Türkçe. `figures/` yoksa
      oluşturulur. `figures/` `.gitignore`'a eklenir (yeniden üretilebilir).

- [ ] **Adım 4: Yeşili doğrula**

- [ ] **Adım 5: Kalite kapısı ve commit** — `feat(plots): add shared Turkish chart style`

## Definition of Done
- [ ] 5 test yeşil
- [ ] `figures/` `.gitignore`'da
- [ ] Sayı biçimi Türkçe (binlik nokta, ondalık virgül)
