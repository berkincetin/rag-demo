# Task 11: Arayüz — metrik paneli + sohbet rozeti

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.9.
> **Önceki:** [Task 10](10-ui-yerel-modeller.md) · **Sonraki:** [Task 12](12-ui-degerlendirme.md)

**Dosyalar:** `pages/3_Metrikler.py`, `app.py` (değişir), `src/rag/ui_state.py` (genişler)
**Test:** `tests/test_ui_state.py` (genişler)

**Üretir:** `format_cost()`, `format_latency()`, `summary_rows()` — sunum yardımcıları.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_ui_state.py — eklenir
from src.rag.ui_state import format_cost, format_latency, summary_rows


def test_cost_is_shown_with_four_decimals():
    assert format_cost(0.00723) == "$0,0072"


def test_unknown_cost_is_labelled_not_zeroed():
    # En kritik biçimlendirme kuralı: fiyatı bilinmeyen model "bedava" görünmemeli.
    assert format_cost(None) == "fiyat girilmedi"


def test_zero_cost_is_shown_as_free_for_local_models():
    assert format_cost(0.0) == "$0,0000"


def test_latency_switches_to_seconds_above_a_thousand_milliseconds():
    assert format_latency(850) == "850 ms"
    assert format_latency(61_400) == "61,4 sn"


def test_summary_rows_flag_partially_priced_models():
    rows = summary_rows([
        _summary(model_id="gpt-4o-mini", runs=3, priced_runs=0, total_cost_usd=None),
        _summary(model_id="claude-opus-5", runs=2, priced_runs=2, total_cost_usd=0.05),
    ])

    by_model = {r["model"]: r for r in rows}
    assert by_model["gpt-4o-mini"]["cost"] == "fiyat girilmedi"
    assert by_model["claude-opus-5"]["cost"] == "$0,0500"


def test_summary_rows_mark_incomplete_pricing():
    rows = summary_rows([_summary(model_id="m", runs=4, priced_runs=2, total_cost_usd=0.02)])

    assert "2/4" in rows[0]["cost"]  # kısmi fiyatlandırma açıkça görünür
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: Yardımcıları yaz**

Türkçe sayı biçimi (virgül ondalık). `format_cost(None)` → `"fiyat girilmedi"`,
**asla `"$0,0000"` değil**. Kısmi fiyatlandırmada `"$0,0200 (2/4 koşu)"`.

- [ ] **Adım 4: Yeşili doğrula** — 6 yeni test

- [ ] **Adım 5: `pages/3_Metrikler.py` yaz**

- **Özet tablosu:** model başına koşu sayısı, ort. gecikme, ort. atıf, kapı isabet oranı,
  toplam maliyet (kısmi fiyatlandırma işaretli)
- **Grafikler:** `st.bar_chart` ile model başına ort. gecikme; model başına toplam maliyet
  (yalnız fiyatı bilinen modeller; grafiğin altına "N model fiyatsız olduğu için grafikte
  yok" notu)
- **Geçmiş tablosu:** son N koşu (soru, model, süre, token, atıf, kapı)
- "Geçmişi temizle" düğmesi — **onay ister**
- ℹ️ Not: **"Sorular metrik veritabanına kaydedilir. Gerçek dağıtımda kişisel veri
  içerebilir."**

- [ ] **Adım 6: `app.py`'yi güncelle (Sohbet sayfası)**

- Başlık altında **aktif model rozeti**: `🤖 claude-opus-5 (anthropic)` / `🖥️ qwen2.5:7b (yerel)`
- Cevabın altında o sorgunun ölçümleri: `⏱ 4,2 sn · 🔤 820→140 token · 💵 $0,0076`
  (fiyat yoksa `💵 fiyat girilmedi`)
- Mevcut Kaynaklar ve Araç çağrıları panelleri **korunur**

- [ ] **Adım 7: Tarayıcıda elle doğrula**

Kontrol listesi:
- [ ] Bir soru sorulduktan sonra cevabın altında süre/token/maliyet görünüyor
- [ ] Aynı soru Metrikler sayfasındaki geçmişte beliriyor
- [ ] İki farklı modelle sorulan sorular özet tablosunda ayrı satır
- [ ] Fiyatsız model "fiyat girilmedi" gösteriyor, `$0,0000` değil
- [ ] Konu dışı soru da geçmişe düşüyor ve kapı sütunu ✗ gösteriyor

- [ ] **Adım 8: Kalite kapısı ve commit**

```bash
git commit -m "feat(ui): add metrics dashboard and per-query cost badge"
```

## Definition of Done
- [ ] 6 test yeşil
- [ ] Fiyatı bilinmeyen model hiçbir yerde `$0` göstermiyor
- [ ] Elle kontrol listesinin 5 maddesi doğrulandı
- [ ] Mevcut Kaynaklar / Araç çağrıları panelleri bozulmadı
