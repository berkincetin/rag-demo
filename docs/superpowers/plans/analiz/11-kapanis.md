# Task 11: Kapanış — Restart & Run All, figürler, README, teslim

> [00-overview.md](00-overview.md) — global kısıtlar. Kabul kriterleri: PRD §4.
> **Önceki:** [Task 10](10-notebook-a7.md)

**Dosyalar:** `notebooks/analiz.ipynb`, `README.md`, `PROGRESSION.md`, `MEMORY.md`

---

- [ ] **Adım 1: Yönetici özeti**

Notebook'un **başına** (veri kalitesi raporundan önce) 7 görevin bulgularını özetleyen
kısa bir bölüm. Her satır notebook'ta hesaplanmış bir sayıya dayanır — özet için ayrıca
hesap yapılmaz, aşağıdaki hücrelerden gelen değerler kullanılır.

- [ ] **Adım 2: Tüm figürleri `figures/` altına yaz**

Her grafik `plots.kaydet(fig, ad)` ile PNG olarak da kaydedilir (README/sunum için).

- [ ] **Adım 3: Restart & Run All**

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/analiz.ipynb
```
Baştan sona **hatasız** bitmeli. Süre ölçülür ve README'ye yazılır.

- [ ] **Adım 4: README Bölüm 2 bölümü**

- Kurulum: `pip install -r requirements-analysis.txt`
- Çalıştırma: `jupyter lab notebooks/analiz.ipynb`
- Yedi görevin nerede olduğu
- 🚨 MF ölçek düzeltmesinin **neden** kritik olduğu (bir paragraf + negatif fiyat örneği)
- Bilinen sınırlılıklar: kısa seriler, nominal fiyat, ayrık ürün setleri

- [ ] **Adım 5: PRD §4 kabul kriterlerini satır satır doğrula**

11 maddenin her biri tek tek işaretlenir. Karşılanmayan varsa **karşılanmadı yazılır**,
sessizce atlanmaz.

- [ ] **Adım 6: PROGRESSION.md ve MEMORY.md güncelle**

- [ ] **Adım 7: Teslim kontrol listesi**

⚠️ Belgeler ve veri seti git'e girmiyor (CLAUDE.md §8). Teslim ZIP'i **elle**
`data/` ve `AI Engineer/bolum2_veriseti.xlsx` içermeli, yoksa değerlendirici ne
`ingest.py`'yi ne notebook'u çalıştırabilir.

- [ ] **Adım 8: Kalite kapısı ve commit** — `docs: close part 2 with executive summary and README`

## Definition of Done
- [x] `Restart & Run All` hatasız — `jupyter nbconvert --execute` temiz `figures/`
      dizininden koştu, 52 hücre, **hatalı hücre: []**
- [x] PRD §4'ün 11 maddesi tek tek doğrulandı (aşağıdaki tablo)
- [x] Figürler `figures/` altında PNG — 10 dosya
- [x] README Bölüm 2 adımlarını, MF ölçek gerekçesini ve 5 sınırlılığı içeriyor
- [x] PROGRESSION.md Bölüm 2'yi kapanmış gösteriyor (11/11)

### PRD §4 kabul kriterleri — doğrulama

| # | Kriter | Sonuç |
|---|---|---|
| 1 | Notebook `Restart & Run All` ile hatasız | ✅ hatalı hücre yok |
| 2 | 7 sorunun her biri için ≥1 grafik | ✅ toplam 10 grafik |
| 3 | 7 sorunun her biri için teknik **ve** iş yorumu | ✅ 7 + 7 |
| 4 | A7'de ≥2 yaklaşım ve pazar bazında MAE/MAPE/RMSE | ✅ 5 model, pazar bazında tablo |
| 5 | A7'de MF katkısı **ablasyonla** ölçülmüş | ✅ `lgbm` vs `lgbm_no_mf` |
| 6 | A4'te p-değeri ve etki büyüklüğü içeren tablo | ✅ Mann-Whitney + Welch + Cliff δ + BH-FDR |
| 7 | MF ölçek düzeltmesi uygulanmış ve gerekçesi gösterilmiş | ✅ düzeltmeli/düzeltmesiz fiyat tablosu |
| 8 | Veri kalitesi raporu notebook başında | ✅ 7 satırlık tablo |
| 9 | Kısa seriler gizlenmemiş, açıkça raporlanmış | ✅ iki ayrı tabloda "yetersiz geçmiş" |
| 10 | Grafiklerde Türkçe eksen etiketi ve başlık | ✅ `plots.stil_uygula` + `tr_sayi` |
| 11 | `pip install -r requirements-analysis.txt` ile kuruluyor | ✅ 9 paket, sürümler `pip freeze`'den |
