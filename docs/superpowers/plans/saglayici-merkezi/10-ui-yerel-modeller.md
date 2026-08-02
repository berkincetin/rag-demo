# Task 10: Arayüz — yerel model yönetimi

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.6, §4.9.
> **Önceki:** [Task 9](09-ui-saglayicilar.md) · **Sonraki:** [Task 11](11-ui-metrikler.md)

**Dosyalar:** `pages/2_Yerel_Modeller.py`, `src/rag/ui_state.py` (genişler)
**Test:** `tests/test_ui_state.py` (genişler)

**Üretir:** `format_size()`, `suggested_models()`, `pull_label()` — sayfanın ihtiyaç
duyduğu saf yardımcılar.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_ui_state.py — eklenir
from src.rag.ui_state import format_size, pull_label, suggested_models


def test_sizes_are_shown_in_gigabytes():
    assert format_size(4_683_087_332) == "4,7 GB"


def test_small_sizes_use_megabytes():
    assert format_size(12_582_912) == "12,0 MB"


def test_unknown_size_is_reported_not_guessed():
    assert format_size(None) == "boyut bilinmiyor"


def test_suggested_models_exclude_already_installed_ones():
    suggested = suggested_models(installed=["qwen2.5:7b-instruct"])

    assert "qwen2.5:7b-instruct" not in suggested


def test_pull_label_shows_percentage_when_total_is_known():
    assert pull_label(status="pulling", fraction=0.25) == "pulling — %25"


def test_pull_label_omits_percentage_when_total_is_unknown():
    # Ollama bazı satırlarda total göndermiyor; uydurma yüzde gösterilmez.
    assert pull_label(status="manifest indiriliyor", fraction=None) == "manifest indiriliyor"
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: Yardımcıları yaz**

`format_size` Türkçe ondalık ayırıcı (virgül) kullanır. `suggested_models` küçük bir
öneri listesi tutar (`qwen2.5:7b-instruct`, `llama3.1:8b`, `gemma2:9b`) ve kuruluları
eler. Öneri listesi **fiyat/performans iddiası içermez** — sadece yaygın seçenekler.

- [ ] **Adım 4: Yeşili doğrula** — 6 yeni test

- [ ] **Adım 5: `pages/2_Yerel_Modeller.py` yaz**

- Üstte Ollama durumu: erişilebilir mi (`is_available()`), değilse **ne yapılacağını
  söyleyen** bir kutu (Ollama'yı başlat / `OLLAMA_BASE_URL` kontrol et)
- Yüklü modeller tablosu: ad, boyut, "Sil" düğmesi (silme **onay** ister)
- İndirme: metin kutusu + öneri listesi + "İndir" düğmesi
- İndirme sırasında `st.progress` + durum metni; `fraction is None` ise çubuk yerine
  belirsiz durum metni gösterilir
- ⚠️ İndirme uzun sürer (4,7 GB); kullanıcıya **"sayfayı kapatmayın"** uyarısı yazılır

- [ ] **Adım 6: Tarayıcıda elle doğrula**

Kontrol listesi:
- [ ] Yüklü modeller listeleniyor, boyutlar doğru biçimlenmiş
- [ ] Küçük bir model indirilirken ilerleme çubuğu ilerliyor
- [ ] İndirme bitince model listede beliriyor ve Sağlayıcılar sayfasında seçilebiliyor
- [ ] Ollama kapalıyken sayfa çökmüyor, açıklayıcı mesaj veriyor

> 💡 Elle test için küçük bir model kullan (`ollama pull qwen2.5:0.5b`, ~400 MB) —
> 4,7 GB'lık modeli test için indirmek gereksiz.

- [ ] **Adım 7: Kalite kapısı ve commit**

```bash
git commit -m "feat(ui): add local model manager with pull progress"
```

## Definition of Done
- [ ] 6 test yeşil
- [ ] İndirme ilerlemesi tarayıcıda gerçekten ilerledi (küçük modelle doğrulandı)
- [ ] Ollama kapalıyken sayfa çökmüyor
- [ ] Bilinmeyen ilerlemede uydurma yüzde gösterilmiyor
