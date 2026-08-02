# Sağlayıcı Merkezi — Uygulama Planı (Genel Bakış)

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ — bu planı task-task uygulamak için
> `superpowers:executing-plans` kullanın. Adımlar `- [ ]` kutucuk sözdizimini kullanır.
>
> **Bu dosyayı + oturum başına tam olarak bir task dosyası okuyun.** Her task dosyası
> kendi kendine yeterlidir: testlerini, kodunu, komutlarını ve beklenen çıktısını taşır.

**Hedef:** Mevcut tek-sağlayıcılı RAG agent'ını, arayüzden sağlayıcı/model seçilebilen,
yerel model indirebilen, token–gecikme–maliyet ölçen ve modelleri sabit bir soru setiyle
otomatik karşılaştırabilen bir platforma dönüştürmek.

**Tasarım dokümanı (önce oku):**
[docs/superpowers/specs/2026-08-02-saglayici-merkezi-tasarim.md](../../specs/2026-08-02-saglayici-merkezi-tasarim.md)

**Ön koşul:** Bölüm 1 Task 1–14 tamamlanmış (14/14 ✅, commit `c57367a`).

---

## Global Kısıtlar

Bunlar **her** task için geçerlidir.

- **Python 3.10.** `str | None` birleşimleri kullanılır; 3.11+ özellikleri (`tomllib`, `Self`) **kullanılmaz**.
- **Kod dili İngilizce**, **kullanıcıya görünen metinler Türkçe** (CLAUDE.md §6).
- **Tüm dosya G/Ç'si UTF-8.** Giriş noktaları `sys.stdout.reconfigure(encoding="utf-8")` çağırır.
- 🚨 **API anahtarları asla diske yazılmaz, loglanmaz, metriğe girmez.** Hata mesajlarında maskelenir.
- 🚨 **Fiyat uydurulmaz.** Doğrulanmamış fiyat `null` kalır; arayüz "girilmedi" gösterir, 0 göstermez.
- 🚨 **Ölçülemeyen token `None`'dır, 0 değildir.**
- **Davranış sözleşmesi:** `tests/test_agent.py` içindeki 7 test **değiştirilmeden** geçmelidir.
- **TDD zorunlu.** Kırmızı test görülmeden üretim kodu yazılmaz.
- **LLM çıktısının metni test edilmez** — non-deterministik. Kontrol akışı mock'lu LLM ile test edilir.
- **Kalite kapısı (her commit öncesi):** `ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70`
- **Commit formatı:** Conventional Commits, **atıf satırı yok**.
- **Yeni bağımlılık sınırı: 15** (10 mevcut + langgraph, langchain-core, anthropic, openai, google-genai).

---

## Task Sırası

| # | Task | Dosya | Üretir |
|---|---|---|---|
| 1 | Model kataloğu ve fiyatlandırma | [01-katalog-fiyat.md](01-katalog-fiyat.md) | `catalog.py`, `pricing.py`, `config/model_prices.json` |
| 2 | Oturum kapsamlı anahtar deposu | [02-kimlik-deposu.md](02-kimlik-deposu.md) | `credentials.py` |
| 3 | Token muhasebesi + Gemini istemcisi | [03-token-ve-gemini.md](03-token-ve-gemini.md) | `TokenUsage`, `GeminiClient`, genişletilmiş `get_client` |
| 4 | Metrik deposu (SQLite) | [04-metrik-deposu.md](04-metrik-deposu.md) | `metrics.py`, `storage/metrics.db` şeması |
| 5 | LangGraph agent migrasyonu 🎯 | [05-langgraph-agent.md](05-langgraph-agent.md) | `graph.py`, `Agent` cephesi |
| 6 | Agent → metrik entegrasyonu | [06-agent-metrik.md](06-agent-metrik.md) | Ölçüm kaydı, `Answer.usage` |
| 7 | Ollama model yöneticisi | [07-ollama-yonetici.md](07-ollama-yonetici.md) | `ollama_admin.py` |
| 8 | Otomatik değerlendirme | [08-degerlendirme.md](08-degerlendirme.md) | `evaluation.py`, soru seti + beklenen kaynaklar |
| 9 | Arayüz: sağlayıcı ve model seçimi | [09-ui-saglayicilar.md](09-ui-saglayicilar.md) | `pages/1_Saglayicilar.py` |
| 10 | Arayüz: yerel model yönetimi | [10-ui-yerel-modeller.md](10-ui-yerel-modeller.md) | `pages/2_Yerel_Modeller.py` |
| 11 | Arayüz: metrik paneli + sohbet rozeti | [11-ui-metrikler.md](11-ui-metrikler.md) | `pages/3_Metrikler.py`, güncellenmiş `app.py` |
| 12 | Arayüz: değerlendirme karşılaştırması | [12-ui-degerlendirme.md](12-ui-degerlendirme.md) | `pages/4_Degerlendirme.py` |
| 13 | Kurulum, Docker otomatik pull, dokümanlar | [13-kurulum-docker-docs.md](13-kurulum-docker-docs.md) | `scripts/setup.py`, `ollama-init`, ADR-011, README |
| — | Doğrulama listesi | [99-dogrulama.md](99-dogrulama.md) | Kabul geçişi |

**Bağımlılık zinciri:** 1 → 2 → 3 → 4 → 5 → 6 → {7, 8} → {9, 10, 11, 12} → 13

Task 1–4 saf mantık (ağ yok, hızlı test). Task 5 en riskli — güvenlik ağını korumak zorunda.
Task 9–12 arayüz; her biri kendi sayfasını ekler ve bağımsız doğrulanır.

---

## Dosya Yapısı (yeni ve değişen)

| Dosya | Durum | Sorumluluk |
|---|---|---|
| `src/rag/catalog.py` | yeni | Sağlayıcı/model kataloğu |
| `src/rag/pricing.py` | yeni | JSON fiyat tablosundan maliyet |
| `src/rag/credentials.py` | yeni | Oturum kapsamlı anahtar deposu |
| `src/rag/metrics.py` | yeni | SQLite ölçüm deposu |
| `src/rag/graph.py` | yeni | LangGraph durum makinesi |
| `src/rag/ollama_admin.py` | yeni | Yerel model list/pull/delete |
| `src/rag/evaluation.py` | yeni | Deterministik kalite puanlaması |
| `src/rag/llm.py` | **değişir** | `TokenUsage`, `GeminiClient`, kimlik enjeksiyonu |
| `src/rag/agent.py` | **değişir** | Grafiği çağıran ince cephe |
| `src/rag/models.py` | **değişir** | `Answer.usage` alanı |
| `app.py` | **değişir** | Model rozeti + sorgu metrikleri |
| `pages/*.py` | yeni | Dört yeni Streamlit sayfası |
| `config/model_prices.json` | yeni | Elle güncellenen fiyat tablosu |
| `scripts/setup.py` | yeni | Ollama kontrolü + model çekme |

---

## Referans Dokümanlar

| Doküman | Ne zaman |
|---|---|
| `docs/superpowers/specs/2026-08-02-saglayici-merkezi-tasarim.md` | **Her task başı** — kararlar ve gerekçeler |
| `docs/04-docker-uctan-uca-test-raporu.md` | Mevcut sistemin ölçülmüş davranışı; metrik hedefleri |
| `docs/bolum1-rag/PRD.md` §7 | Değerlendirme soru seti (Task 8) |
| `MEMORY.md` | Ölçülmüş tuzaklar — özellikle sıcaklık, prompt kırılganlığı, atıf |

## Nerede Kaldık

Aktif task ve sıradaki adım: [PROGRESSION.md](../../../../PROGRESSION.md).
