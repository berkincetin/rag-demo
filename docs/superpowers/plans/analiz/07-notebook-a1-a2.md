# Task 7: Notebook açılışı, veri kalitesi raporu, A1 ve A2

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5 (A1, A2), PRD §4.
> **Önceki:** [Task 6](06-tahmin-lgbm.md) · **Sonraki:** [Task 8](08-notebook-a3-a4.md)

**Dosyalar:** `notebooks/analiz.ipynb` · **Test:** notebook'un kendisi (çalışması) +
`tests/test_analysis_notebook.py` (yardımcı fonksiyonlar varsa)

Bu ve sonraki üç task **notebook** üretir. Notebook ince kalır: hesap modüllerde,
notebook'ta çağrı + grafik + yorum. Her görevin altında **iki ayrı başlık**:
`#### Teknik yorum` ve `#### İş yorumu` (PRD §4 kabul kriteri).

---

- [ ] **Adım 1: Notebook iskeleti ve veri kalitesi raporu**

Hücreler: başlık → kurulum/import → `load_raw()` → `clean()` → rapor tablosu.
Rapor tablosu `DataQualityReport`'ndan gelir; **hangi kayıt kaç kez düzeltildi**
şeffaf yazılır. Kısa seriler ayrı tabloda listelenir (gizlenmez — PRD §4).

- [ ] **Adım 2: A1 — son 2 yıl satış performansı**

- Filtre: Şirket 1, `tarih >= 2024-05-01` (V1 — verinin son ayı 2026-04).
- Grafik 1: 2×2 subplot, dört pazar, ikili eksen (Brüt Kutu bar + Net TL çizgi).
- Grafik 2: pazar başına ürün katkısı (yığılmış alan) + Pareto tablosu.
- Zirve/dip ay tablosu: ay ortalamasının genel ortalamaya oranı, dört pazar yan yana.
- Yorumlar.

- [ ] **Adım 3: A2 — pazar payı ve rekabet pozisyonu**

- Pay `brut_kutu` üzerinden, pazar-ay bazında %.
- Grafik: dört pazar için yığılmış alan (2016→2026), üç şirket.
- HHI zaman serisi — yoğunlaşma artıyor mu?
- "Orantısız pay": pazar CAGR'ı vs Şirket 1 CAGR'ı farkı tablosu.
- Yorumlar.

⚠️ Bulgular §2.2'deki ham pay tablosu (A %12,4 / B %13,1 / C %6,0 / D %3,9) bir
**beklenti**dir, sonuç değil. Temizlenmiş veriyle çıkan sayı farklıysa **çıkan sayı
yazılır** ve fark açıklanır.

- [ ] **Adım 4: Notebook'u baştan çalıştır** — `jupyter nbconvert --execute` ile
      hatasız bitmeli; çıktılar kaydedilir.

- [ ] **Adım 5: Kalite kapısı ve commit** — `feat(notebook): add data quality report and tasks A1-A2`

## Definition of Done
- [ ] Notebook buraya kadar `--execute` ile hatasız koşuyor
- [ ] Veri kalitesi raporu sayılarla dolu, uydurma yok
- [ ] A1 ve A2'nin her birinde ≥1 grafik
- [ ] A1 ve A2'nin her birinde teknik **ve** iş yorumu ayrı başlık altında
- [ ] Kısa seriler açıkça listelenmiş
