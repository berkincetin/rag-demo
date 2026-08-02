# Task 13: Kurulum, Docker otomatik pull, dokümanlar

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §5, §2.1.
> **Önceki:** [Task 12](12-ui-degerlendirme.md) · **Sonraki:** [Doğrulama](99-dogrulama.md)

**Dosyalar:** `scripts/setup.py`, `docker-compose.yml`, `Dockerfile`, `README.md`,
`docs/02-karar-kaydi.md`, `.env.example`
**Test:** `tests/test_setup.py`

- [ ] **Adım 1: Kurulum betiği için kırmızı test**

```python
# tests/test_setup.py
from scripts.setup import SetupPlan, plan_setup


def test_missing_ollama_yields_install_instructions_not_an_auto_install():
    # İşletim sistemi seviyesinde kurulum kullanıcının onayı olmadan yapılmaz.
    plan = plan_setup(ollama_running=False, installed_models=[], platform="win32")

    assert plan.action == "instruct"
    assert "ollama.com" in plan.message


def test_running_ollama_without_the_model_yields_a_pull():
    plan = plan_setup(ollama_running=True, installed_models=[], platform="win32")

    assert plan.action == "pull"
    assert plan.model


def test_everything_present_is_a_no_op():
    plan = plan_setup(
        ollama_running=True, installed_models=["qwen2.5:7b-instruct"], platform="linux"
    )

    assert plan.action == "ok"


def test_a_quantised_variant_counts_as_installed():
    # Yerelde q4_K_M soneki var; düz etiketi aramak gereksiz 4,7 GB indirir.
    plan = plan_setup(
        ollama_running=True,
        installed_models=["qwen2.5:7b-instruct-q4_K_M"],
        platform="win32",
    )

    assert plan.action == "ok"
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `scripts/setup.py` yaz**

`plan_setup()` saf fonksiyon (test edilir); `main()` onu çalıştırır ve raporlar.
Ollama yoksa **platforma uygun kurulum komutunu yazdırır ve çıkar** — otomatik kurmaz.
Kuantize sonek eşleşmesi Task 11'de (Bölüm 1) öğrenilen tuzağı kapatır.

- [ ] **Adım 4: Yeşili doğrula** — 4 test

- [ ] **Adım 5: Docker'da otomatik model çekme**

`docker-compose.yml`'e üçüncü servis:

```yaml
  ollama-init:
    image: ollama/ollama:latest
    depends_on: [ollama]
    environment:
      OLLAMA_HOST: http://ollama:11434
    entrypoint: ["sh", "-c", "until ollama list >/dev/null 2>&1; do sleep 2; done;
                 ollama pull ${LLM_MODEL:-qwen2.5:7b-instruct}"]
    restart: "no"
```

`rag` servisi `depends_on` listesine `ollama-init` eklenir
(`condition: service_completed_successfully`). README'deki elle `exec` adımı kalkar.

⚠️ İlk `up` uzun sürer (~4,7 GB indirme) — README'de belirtilir.

- [ ] **Adım 6: Dokümanlar**

| Doküman | Değişiklik |
|---|---|
| `docs/02-karar-kaydi.md` | **ADR-011** eklenir: LangGraph benimsendi, gerekçe + ADR-001 "superseded by ADR-011" işaretlenir. **ADR-012**: anahtarlar yalnız oturum belleğinde. **ADR-013**: fiyatlar elle güncellenen JSON'da, doğrulanmamış fiyat `null` |
| `README.md` | Yeni bölümler: **Sağlayıcı ve model seçimi**, **Yerel model yönetimi**, **Metrikler ve maliyet**, **Model karşılaştırması**. Bağımlılık sayısı 15'e güncellenir. Docker bölümünden elle `pull` adımı kaldırılır. Güvenlik notu: anahtarlar diske yazılmaz; sorular metrik veritabanına yazılır |
| `.env.example` | `GEMINI_API_KEY`, `OLLAMA_PULL_TIMEOUT` eklenir |
| `MEMORY.md` | Task 8'de ölçülen değerlendirme taban çizgisi |
| `PROGRESSION.md` | Yeni aşama tablosu (13 task), Bölüm 2'nin hâlâ beklediği notu |

- [ ] **Adım 7: Docker'ı uçtan uca doğrula**

```bash
docker compose down -v          # ollama volume'ü de siler — temiz kurulum testi
docker compose up --build -d
docker compose exec rag python scripts/smoke_test.py
```
Beklenen: elle `ollama pull` **çalıştırmadan** `Başarısız kontrol sayısı: 0`.

- [ ] **Adım 8: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git commit -m "docs: add provider hub setup, Docker auto-pull, and ADR-011..013"
```

## Definition of Done
- [ ] 4 test yeşil
- [ ] `docker compose up` sonrası elle pull **olmadan** smoke test 0 hata
- [ ] ADR-011/012/013 yazıldı, ADR-001 superseded işaretlendi
- [ ] README dört yeni bölümü ve güvenlik notlarını içeriyor
- [ ] Ollama otomatik **kurulmuyor**, yalnız komut gösteriliyor
