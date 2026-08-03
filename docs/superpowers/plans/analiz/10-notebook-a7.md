# Task 10: A7 — talep tahmini, model karşılaştırması, MF ablasyonu

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: TRD §5 (A7).
> **Önceki:** [Task 9](09-notebook-a5-a6.md) · **Sonraki:** [Task 11](11-kapanis.md)

**Dosyalar:** `notebooks/analiz.ipynb` (genişletme)

---

- [ ] **Adım 1: Beş modeli walk-forward ile koştur**

`naive`, `snaive`, `ma3`, `lgbm`, `lgbm_no_mf` — hepsi **aynı** 12 aylık genişleyen
pencere bölmelerinde. Hedef: Şirket 1'in her ürün-pazar serisi için t+1 `brut_kutu`.

- [ ] **Adım 2: Tablo 1 — model × pazar → MAE, MAPE, RMSE, WAPE**

Case'in doğrudan istediği tablo. **Pazar bazında** — genel ortalama tek başına
yanıltıcı olur (18 serinin 10'u A Pazarı'nda).

- [ ] **Adım 3: Tablo 2 — MF ablasyonu**

`lgbm` vs `lgbm_no_mf`, pazar bazında delta. Case'in "MF Oranı tahmin gücünü artırıyor mu?"
sorusunun doğrudan cevabı. 🚨 **Artırmıyorsa artırmıyor yazılır.** Negatif sonuç da sonuçtur.

- [ ] **Adım 4: Tablo 3 — mevsimsellik gücüne göre model sıralaması**

Yüksek/düşük mevsimsellikli seriler ayrımında hangi model kazanıyor →
"aynı mimari her pazarda geçerli mi?" sorusunun cevabı. Bulgular §2.5'e göre beklenen
cevap **hayır**; gerekçesi seri uzunluğu + mevsimsellik gücü. Ölçüm ne diyorsa o yazılır.

- [ ] **Adım 5: Grafik — gerçek vs tahmin**

Seçilmiş temsili seriler (her pazardan en az bir tane), son 12 ay, en iyi model +
naive baseline birlikte.

- [ ] **Adım 6: Kısa seri politikası tablosu**

`C/Ürün 1` (1 ay), `D/Ürün 78` (11 ay), `B/Ürün-FP` (27 ay) → "yetersiz geçmiş"
etiketiyle ayrı gösterilir. Global modelin eğitim havuzunda kalırlar ama per-seri
metrik tablosunda ayrı satırdadırlar. **Gizlenmez, uydurulmaz.**

- [ ] **Adım 7: Notebook'u baştan çalıştır** — toplam süre ölçülür ve yazılır

- [ ] **Adım 8: Kalite kapısı ve commit** — `feat(notebook): add demand forecasting with model comparison`

## Definition of Done
- [ ] ≥2 yaklaşım (baseline + ML) karşılaştırılmış
- [ ] MAE/MAPE/RMSE **pazar bazında** tabloda
- [ ] MF katkısı **ablasyonla** ölçülmüş
- [ ] Gerçek vs tahmin grafiği var
- [ ] Kısa seriler ayrı etiketle raporlanmış
- [ ] Teknik + iş yorumu
