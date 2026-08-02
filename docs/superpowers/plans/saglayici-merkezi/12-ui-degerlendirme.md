# Task 12: Arayüz — değerlendirme karşılaştırması

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.8, §4.9.
> **Önceki:** [Task 11](11-ui-metrikler.md) · **Sonraki:** [Task 13](13-kurulum-docker-docs.md)

**Dosyalar:** `pages/4_Degerlendirme.py`, `src/rag/ui_state.py` (genişler)
**Test:** `tests/test_ui_state.py` (genişler)

**Üretir:** `estimate_eval_cost()`, `comparison_rows()`

🚨 **Bu sayfa para harcar.** Bulut modelleriyle 13 soruluk set çalıştırmak ücretlidir.
Çalıştırmadan **önce** tahmini maliyet gösterilir ve açık onay alınır.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_ui_state.py — eklenir
from src.rag.ui_state import comparison_rows, estimate_eval_cost


def test_cost_estimate_scales_with_the_case_count():
    # Kaba tahmin: vaka sayısı × ortalama token × birim fiyat
    estimate = estimate_eval_cost("claude-opus-5", cases=13)

    assert estimate is not None
    assert estimate > 0


def test_estimate_is_none_for_an_unpriced_model():
    assert estimate_eval_cost("gpt-4o-mini", cases=13) is None


def test_local_models_are_estimated_as_free():
    assert estimate_eval_cost("qwen2.5:7b-instruct", cases=13) == 0.0


def test_comparison_orders_by_citation_rate_then_latency():
    rows = comparison_rows([
        _result(model_id="a", citation_rate=0.8, avg_latency_ms=1000),
        _result(model_id="b", citation_rate=1.0, avg_latency_ms=5000),
        _result(model_id="c", citation_rate=1.0, avg_latency_ms=2000),
    ])

    assert [r["model"] for r in rows] == ["c", "b", "a"]


def test_unmeasured_rates_are_shown_as_dash_not_zero():
    rows = comparison_rows([_result(model_id="a", citation_rate=None)])

    assert rows[0]["citation_rate"] == "—"
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: Yardımcıları yaz**

`estimate_eval_cost` **kaba** bir tahmindir ve arayüzde böyle etiketlenir
("yaklaşık, ±%50"). Vaka başına varsayılan token tahmini bir sabittir ve nereden geldiği
yorumda yazar (Task 6'daki gerçek ölçümlerin ortalaması). Fiyat yoksa `None`.

`comparison_rows` sıralaması: `citation_rate` azalan → `avg_latency_ms` artan.
`None` oranlar `"—"` gösterilir, sıralamada en sona düşer.

- [ ] **Adım 4: Yeşili doğrula** — 5 yeni test

- [ ] **Adım 5: `pages/4_Degerlendirme.py` yaz**

Akış:
1. Kullanılabilir modellerden **çoklu seçim** (`st.multiselect`)
2. Seçim yapılınca **tahmini toplam maliyet** ve **tahmini süre** gösterilir
   (yerel model için: "≈ N × 40–460 sn, uzun sürebilir")
3. `st.checkbox("Maliyeti anladım, çalıştır")` işaretlenmeden düğme **etkin değil**
4. Çalışırken model başına ilerleme (`st.status`)
5. Sonuç: karşılaştırma tablosu (atıf oranı, kaynak isabeti, kanıt isabeti, red isabeti,
   ort. gecikme, toplam maliyet) + `st.bar_chart`
6. Sonuçlar metrik deposuna da yazılır (Task 6 üzerinden zaten yazılıyor)

⚠️ Uzun süren iş: Streamlit tek iş parçacığında çalışır; sayfa bloke olur. Kullanıcıya
**"bu işlem dakikalar sürebilir, sekmeyi kapatmayın"** uyarısı yazılır.

- [ ] **Adım 6: Tarayıcıda elle doğrula**

Kontrol listesi:
- [ ] Onay kutusu işaretlenmeden "Çalıştır" düğmesi devre dışı
- [ ] Tahmini maliyet çalıştırmadan önce görünüyor
- [ ] Fiyatı olmayan model seçilince maliyet "bilinmiyor" diyor
- [ ] En az bir yerel model için değerlendirme tamamlanıp tablo çıkıyor
- [ ] Tablo atıf oranına göre sıralı

> 💡 Elle testte **yalnız yerel model** kullan — bulut çağrısı için kullanıcının kendi
> anahtarı ve parası gerekir; onay olmadan harcama yapılmaz.

- [ ] **Adım 7: Kalite kapısı ve commit**

```bash
git commit -m "feat(ui): add model evaluation and comparison page with cost consent"
```

## Definition of Done
- [ ] 5 test yeşil
- [ ] Onay kutusu olmadan çalıştırma mümkün değil
- [ ] Tahmini maliyet çalıştırmadan önce gösteriliyor ve "yaklaşık" etiketli
- [ ] En az bir yerel modelle uçtan uca değerlendirme tarayıcıda tamamlandı
