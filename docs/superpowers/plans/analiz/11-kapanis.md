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
- [ ] `Restart & Run All` hatasız — komut çıktısıyla kanıtlanmış
- [ ] PRD §4'ün 11 maddesi tek tek işaretlenmiş
- [ ] Figürler `figures/` altında PNG
- [ ] README Bölüm 2 adımlarını ve sınırlılıkları içeriyor
- [ ] PROGRESSION.md Bölüm 2'yi kapanmış gösteriyor
