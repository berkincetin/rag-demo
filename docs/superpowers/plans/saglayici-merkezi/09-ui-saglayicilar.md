# Task 9: Arayüz — sağlayıcı ve model seçimi

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.9.
> **Önceki:** [Task 8](08-degerlendirme.md) · **Sonraki:** [Task 10](10-ui-yerel-modeller.md)

**Dosyalar:** `pages/1_Saglayicilar.py`, `src/rag/ui_state.py`
**Test:** `tests/test_ui_state.py`

Streamlit sayfaları kapsam dışıdır (`pyproject.toml` omit). Bu yüzden **tüm mantık**
`ui_state.py`'ye çıkarılır ve orası test edilir; sayfa dosyası yalnız widget çizer.

**Üretir:** `get_store(session)`, `set_key(session, provider, key)`,
`available_models(session)`, `active_model(session)`, `provider_status(session)`

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_ui_state.py
from src.rag.ui_state import (
    active_model, available_models, provider_status, set_active_model, set_key,
)


def test_only_local_models_are_available_without_any_key():
    session = {}

    models = available_models(session, local_models=["qwen2.5:7b"])

    assert [m.id for m in models] == ["qwen2.5:7b"]


def test_adding_a_key_unlocks_that_providers_models():
    session = {}
    set_key(session, "anthropic", "sk-ant-test")

    ids = [m.id for m in available_models(session, local_models=[])]

    assert "claude-opus-5" in ids
    assert "gpt-4o-mini" not in ids  # OpenAI anahtarı girilmedi


def test_provider_status_masks_the_key():
    session = {}
    set_key(session, "openai", "sk-supersecretvalue")

    status = provider_status(session)["openai"]

    assert status.configured is True
    assert "supersecret" not in status.masked


def test_active_model_defaults_to_the_configured_local_model():
    session = {}

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"


def test_selecting_a_model_without_its_key_is_rejected():
    session = {}

    with pytest.raises(ValueError, match="anahtar"):
        set_active_model(session, "claude-opus-5")


def test_selecting_a_model_after_adding_its_key_succeeds():
    session = {}
    set_key(session, "anthropic", "sk-ant-test")

    set_active_model(session, "claude-opus-5")

    assert active_model(session, local_models=[]).id == "claude-opus-5"


def test_removing_a_key_falls_back_to_a_local_model():
    session = {}
    set_key(session, "anthropic", "sk-ant-test")
    set_active_model(session, "claude-opus-5")

    set_key(session, "anthropic", "")  # anahtar temizlendi

    assert active_model(session, local_models=["qwen2.5:7b"]).id == "qwen2.5:7b"
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `ui_state.py` yaz**

`session` bir `MutableMapping` olarak geçer (`st.session_state` uyumlu, ama Streamlit'e
bağımlılık **yok** — testler düz `dict` kullanır). İçeride Task 2'nin
`SessionCredentialStore`'unu tutar.

`available_models` = yerel modeller (Task 7'den gelen liste) + anahtarı girilmiş bulut
sağlayıcılarının katalog modelleri. Aktif model geçersizleşirse yerel modele düşer.

- [ ] **Adım 4: Yeşili doğrula** — 7 test geçmeli

- [ ] **Adım 5: `pages/1_Saglayicilar.py` yaz**

- Sağlayıcı başına `st.text_input(..., type="password")` + "Kaydet" düğmesi
- Durum rozeti: ✅ girildi (maskeli) / ⬜ girilmedi
- ℹ️ Bilgi kutusu: **"Anahtarlar yalnızca bu oturumun belleğinde tutulur, diske
  yazılmaz. Sekmeyi kapattığınızda silinir."**
- Model seçimi `st.selectbox` — yalnız kullanılabilir modeller
- Seçili modelin fiyatı bilinmiyorsa ⚠️ **"Bu model için fiyat girilmedi; maliyet
  hesaplanmayacak"** uyarısı (`config/model_prices.json` düzenlenebilir, yolu yazılır)

- [ ] **Adım 6: Tarayıcıda elle doğrula**

```bash
streamlit run app.py
```
Kontrol listesi:
- [ ] Anahtar girilmeden yalnız yerel model seçilebiliyor
- [ ] Anahtar girilince o sağlayıcının modelleri listeye giriyor
- [ ] Girilen anahtar ekranda maskeli görünüyor
- [ ] Fiyatı olmayan modelde uyarı çıkıyor
- [ ] Sayfa yenilenince anahtar **kayboluyor** (oturum belleği kanıtı)

- [ ] **Adım 7: Kalite kapısı ve commit**

```bash
git commit -m "feat(ui): add provider settings page with session-only API keys"
```

## Definition of Done
- [ ] 7 test yeşil, `ui_state.py` ≥ %95 kapsanmış
- [ ] Sayfa dosyasında iş mantığı yok (yalnız widget)
- [ ] Elle kontrol listesinin 5 maddesi de doğrulandı
- [ ] Anahtar diske yazılmadığı tarayıcıda gösterildi (yenile → kayboldu)
