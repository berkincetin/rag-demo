# Tasarım — Sağlayıcı Merkezi, Model Yönetimi ve Metrik Paneli

**Tarih:** 2026-08-02 · **Durum:** Onay bekliyor · **Kapsam:** Bölüm 1 RAG Agent genişletmesi

Bu doküman, mevcut RAG agent'ını tek-sağlayıcılı bir demodan **çok sağlayıcılı, ölçülebilir
bir platforma** dönüştüren genişletmenin tasarımıdır. Uygulama planı
[docs/superpowers/plans/saglayici-merkezi/](../plans/saglayici-merkezi/) altındadır.

---

## 1. Neden

Mevcut sistem tek bir yerel modele bağlı ve o modelin zayıflıkları ölçülmüş durumda:
tool-calling kırılgan, atıf işaretlemesi isabetsiz, CPU'da soru başına 40–460 saniye
(bkz. [04-docker-uctan-uca-test-raporu.md](../../04-docker-uctan-uca-test-raporu.md)).
"Bulut sağlayıcıya geçmek iyileştirir" cümlesi şu an bir **iddia**; bu genişletme onu
ölçülebilir bir **veri**ye çeviriyor.

Hedef: aynı soruyu farklı modellerle çalıştırıp kalite, gecikme ve maliyeti yan yana
görebilmek — ve bunu kod değiştirmeden, arayüzden yapabilmek.

---

## 2. Alınan kararlar

| Karar | Seçim | Gerekçe |
|---|---|---|
| Sıralama | Genişletme önce, Bölüm 2 sonra | Kullanıcı kararı (2026-08-02) |
| Agent mimarisi | **LangGraph'a taşınır** | Kullanıcı kararı. ADR-001 (ham Python) iptal → ADR-011 |
| API anahtarı saklama | **Yalnız oturum belleği** | Diske hiç yazılmaz; sekme kapanınca gider |
| Metrik derinliği | **Kalıcı geçmiş + otomatik kalite değerlendirmesi** | Model karşılaştırması ancak geçmişle mümkün |

### 2.1 ADR-001 iptali

ADR-001 "LangChain/LlamaIndex yok, ham Python" diyordu ve gerekçesi *"demo ölçeğinde
soyutlama katmanı fayda değil borç üretir"* idi. Genişletilmiş kapsamda bu gerekçe
geçerliliğini yitiriyor: dallanma (onarım turu, enjeksiyon, çok sağlayıcılı yönlendirme),
her düğümün ayrı ölçülmesi ve akış görselleştirmesi ham döngüde elle yazılacak şeyler.
**ADR-011** bunu kayda geçirir; ADR-001 "süperseded by ADR-011" olarak işaretlenir.

⚠️ **Risk:** LangGraph, ham döngüde 52 satırda çözülen bir işi bir grafik soyutlamasına
taşıyor ve 3 katmanlı güvenlik ağının davranışı **birebir korunmak zorunda**. Mevcut 7
agent testi bu yüzden **değiştirilmeden** yeşil kalmalı — migrasyonun kabul kriteri budur.

---

## 3. Mimari

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT ÇOK SAYFALI ARAYÜZ                          │
│                                                                              │
│  💬 Sohbet          ⚙️ Sağlayıcılar      📦 Yerel Modeller                   │
│  soru + cevap        anahtar girişi       ollama pull / list / rm            │
│  + kaynak + iz       + model seçimi       + indirme ilerlemesi              │
│                                                                              │
│  📊 Metrikler        🎯 Değerlendirme                                        │
│  token/maliyet/      sabit soru setiyle                                      │
│  gecikme geçmişi     otomatik puanlama                                       │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ st.session_state["credentials"]  (RAM, diske yazılmaz)
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      AGENT — LangGraph durum makinesi                        │
│                                                                              │
│   [giriş] → skor_kapisi ─(güvensiz)→ [red]                                   │
│                  │ (güvenli)                                                 │
│                  ▼                                                           │
│              llm_turu ──(tool çağrısı)──► arac_calistir ──┐                  │
│                  │ ▲                                       │                 │
│                  │ └───────────────────────────────────────┘ (max 3 tur)     │
│                  │ (cevap, tool yok & çıktı yok) → baglam_enjekte ──┘         │
│                  ▼                                                           │
│              atif_kontrol ──(atıf yok)──► onarim_turu ──► atif_kontrol       │
│                  │ (atıf var)                    │ (yine yok)                │
│                  ▼                               ▼                           │
│               [cevap]                        [bilgi yok]                     │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ her düğüm çıkışında ölçüm kaydı
                                ▼
┌────────────────────────────┐  ┌──────────────────────────────────────────────┐
│  LLM SAĞLAYICI KATMANI     │  │  METRİK DEPOSU (SQLite, storage/metrics.db)  │
│  ollama · anthropic ·      │  │  run(id, ts, model, soru, gecikme,           │
│  openai · gemini           │  │      giris_token, cikis_token, maliyet,      │
│  + model kataloğu          │  │      atif_sayisi, kapi_gecti, tool_sayisi)   │
└────────────────────────────┘  └──────────────────────────────────────────────┘
```

---

## 4. Bileşenler

Her bileşen tek sorumluluk taşır, kendi arayüzü üzerinden konuşur ve ayrı test edilir.

### 4.1 `src/rag/catalog.py` — model kataloğu

Sağlayıcı ve model tanımlarının **tek kaynağı**. Saf veri + saf fonksiyon; ağ erişimi yok.

```python
@dataclass(frozen=True)
class ModelInfo:
    id: str              # "claude-opus-5", "qwen2.5:7b-instruct"
    provider: str        # "anthropic" | "openai" | "gemini" | "ollama"
    label: str           # arayüzde görünen ad
    context_tokens: int | None
    local: bool          # yerelde mi çalışıyor
```

`list_models(provider=None)`, `get_model(id)`, `providers()` fonksiyonlarını verir.
Yerel modeller katalogda **sabit değil** — çalışma zamanında Ollama'dan okunur (§4.6).

### 4.2 `src/rag/pricing.py` — maliyet hesabı

Fiyatlar koda gömülmez; `config/model_prices.json` dosyasından okunur.

```json
{
  "_kaynak": "Anthropic fiyatları 2026-06-24 tarihli resmî tablodan; 1M token başına USD",
  "claude-opus-5":   {"input": 5.00,  "output": 25.00},
  "claude-sonnet-5": {"input": 3.00,  "output": 15.00},
  "claude-haiku-4-5":{"input": 1.00,  "output": 5.00},
  "gpt-4o-mini":     {"input": null,  "output": null},
  "gemini-2.0-flash":{"input": null,  "output": null},
  "__local__":       {"input": 0.0,   "output": 0.0}
}
```

🚨 **Fiyat uydurulmaz.** Yalnızca Anthropic fiyatları doğrulanmış kaynaktan geliyor.
OpenAI ve Gemini için `null` bırakılıyor; `estimate_cost()` `null` görürse `None` döner
ve arayüz **"fiyat girilmedi"** rozeti gösterir — sıfır ya da tahmini bir sayı **göstermez**.
Yerel modellerin maliyeti tanımı gereği 0'dır (elektrik hariç, bu not arayüzde yazar).

### 4.3 `src/rag/credentials.py` — oturum kapsamlı anahtar deposu

```python
class CredentialStore(Protocol):
    def set(self, provider: str, key: str) -> None: ...
    def get(self, provider: str) -> str | None: ...
    def providers_with_keys(self) -> list[str]: ...
```

Tek uygulama: `SessionCredentialStore` — Streamlit `st.session_state` içinde tutar.
**Diske yazma yolu yoktur**; sınıfta dosya G/Ç'si bulunmaması testle korunur.
Anahtarlar loglanmaz, metrik kaydına girmez, hata mesajlarında maskelenir (`sk-…abcd`).

Ortam değişkeni (`ANTHROPIC_API_KEY` vb.) hâlâ desteklenir ve **oturum anahtarı yoksa**
yedek olarak kullanılır — CLI ve Docker akışları bozulmasın diye.

### 4.4 `src/rag/llm.py` — sağlayıcı istemcileri (genişletme)

Mevcut `LLMClient` protokolü, `LLMResponse`, `ToolCall` **değişmez**. Eklenenler:

- `GeminiClient` — `google-genai` SDK'sı üzerinden
- Her istemciye `usage: TokenUsage` alanı: `(input_tokens, output_tokens)`
- `get_client(config, credentials=None)` — anahtar kaynağı olarak store'u kabul eder

Token sayıları sağlayıcıya göre farklı yerlerden okunur ve tek şekle normalize edilir:

| Sağlayıcı | Giriş | Çıkış |
|---|---|---|
| Ollama | `prompt_eval_count` | `eval_count` |
| Anthropic | `usage.input_tokens` | `usage.output_tokens` |
| OpenAI | `usage.prompt_tokens` | `usage.completion_tokens` |
| Gemini | `usage_metadata.prompt_token_count` | `usage_metadata.candidates_token_count` |

Alan yoksa `None` döner — **0 yazılmaz**, çünkü 0 "ölçüldü ve sıfır" anlamına gelir.

### 4.5 `src/rag/graph.py` — LangGraph agent

Mevcut `Agent.answer()` davranışını grafiğe taşır. Durum:

```python
class AgentState(TypedDict):
    question: str
    messages: list[dict]
    tool_outputs: list[str]
    trace: list[dict]
    final_text: str
    citations: list[str]
    repaired: bool        # onarım turu kullanıldı mı
    usage: TokenUsage
```

Düğümler ve kenarlar §3'teki diyagramdaki gibidir. **Davranış sözleşmesi:**
mevcut `tests/test_agent.py` içindeki 7 test **tek satır değiştirilmeden** geçmelidir.
`Agent` sınıfı ince bir cephe (facade) olarak kalır ve grafiği çağırır — CLI, Streamlit
ve smoke test'in içe aktarımları bozulmaz.

### 4.6 `src/rag/ollama_admin.py` — yerel model yöneticisi

Ollama HTTP API'si üzerinden: `list_local()`, `pull(model, on_progress)`, `delete(model)`.
`pull` akış (streaming) yanıtı okuyup ilerleme yüzdesini geri çağırır — arayüz çubuğu
bunu gösterir. Ollama erişilemezse **anlaşılır bir hata** döner, çökme olmaz.

### 4.7 `src/rag/metrics.py` — ölçüm deposu

SQLite (`storage/metrics.db`), tek tablo:

| sütun | tip | açıklama |
|---|---|---|
| `id` | INTEGER PK | |
| `ts` | TEXT | ISO-8601 |
| `model_id` / `provider` | TEXT | |
| `question` | TEXT | |
| `latency_ms` | INTEGER | uçtan uca |
| `input_tokens` / `output_tokens` | INTEGER NULL | ölçülemezse NULL |
| `cost_usd` | REAL NULL | fiyat yoksa NULL |
| `citation_count` | INTEGER | |
| `gate_passed` | INTEGER | 0/1 |
| `tool_calls` | INTEGER | |
| `repaired` | INTEGER | onarım turu tetiklendi mi |

`record(run)` ve `summary_by_model()` fonksiyonları. SQLite seçildi çünkü stdlib'de var
(yeni bağımlılık yok), tek dosya, eşzamanlı okuma yeterli.

### 4.8 `src/rag/evaluation.py` — otomatik kalite değerlendirmesi

Sabit soru seti (PRD §7'deki 8 demo sorusu + 5 konu dışı) üzerinden **deterministik**
puanlama. LLM-as-judge **kullanılmaz** — non-deterministik ve pahalı olurdu. Ölçülenler:

| Metrik | Nasıl ölçülür |
|---|---|
| `citation_rate` | Geçerli sorularda atıflı cevap oranı |
| `source_accuracy` | Atıf edilen dosyanın beklenen dosya olması (beklenen kaynaklar sabit) |
| `refusal_accuracy` | Konu dışı soruların reddedilme oranı |
| `evidence_hit` | Beklenen kanıt metninin cevapta geçmesi (ör. `1.500 TL/ay`) |
| `avg_latency_ms`, `total_cost_usd` | Metrik deposundan |

Çıktı: model başına satır → arayüzde sıralanabilir tablo. Cevap **metni** hiçbir zaman
test edilmez; ölçülen şey atıf ve kapı davranışıdır.

### 4.9 Arayüz — Streamlit çok sayfalı

`app.py` giriş noktası kalır, sayfalar `pages/` altına:

| Sayfa | İçerik |
|---|---|
| `app.py` (💬 Sohbet) | Mevcut arayüz + **aktif model rozeti** + cevabın altında o sorgunun token/süre/maliyeti |
| `pages/1_Saglayicilar.py` | Sağlayıcı başına anahtar girişi (`type="password"`), doğrulama düğmesi, model seçimi |
| `pages/2_Yerel_Modeller.py` | Yüklü modeller, indirme kutusu + ilerleme çubuğu, silme |
| `pages/3_Metrikler.py` | Geçmiş tablosu + model bazında toplam/ortalama grafikleri (`st.bar_chart`) |
| `pages/4_Degerlendirme.py` | Seçili modeller için değerlendirmeyi çalıştır → karşılaştırma tablosu |

Grafikler için yeni bağımlılık yok; Streamlit'in yerleşik grafik fonksiyonları kullanılır.

---

## 5. Kurulum: Ollama + model otomatik gelsin

| Ortam | Yaklaşım |
|---|---|
| **Docker** | `docker-compose.yml`'e `ollama-init` servisi eklenir: ollama sağlıklı olunca `ollama pull` çalıştırır, çıkar. `rag` servisi `depends_on: ollama-init` ile bekler. Elle `exec` adımı kalkar |
| **Yerel** | `scripts/setup.py`: Ollama kurulu mu bakar (`/api/version`), değilse **platforma uygun kurulum komutunu yazdırır** ve durur. Kuruluysa modeli çeker |

⚠️ Ollama'yı **otomatik kurmayız** — işletim sistemi seviyesinde kurulum (winget/brew/curl)
kullanıcının onayı olmadan yapılmamalı. Betik komutu gösterir, kullanıcı çalıştırır.

---

## 6. Yeni bağımlılıklar

Mevcut çalışma zamanı bağımlılığı 10. Eklenenler:

| Paket | Neden | Zorunlu mu |
|---|---|---|
| `langgraph` + `langchain-core` | Agent grafiği (ADR-011) | Evet |
| `anthropic` | Claude sağlayıcısı | Evet (artık varsayılan yollardan biri) |
| `openai` | OpenAI sağlayıcısı | Evet |
| `google-genai` | Gemini sağlayıcısı | Evet |

Toplam çalışma zamanı: **10 → 15**. Overview'daki "max 12" kısıtı bu genişletmede
**bilinçli olarak aşılıyor**; yeni sınır 15 olarak kayda geçer. SQLite ve grafikler için
ek bağımlılık yok (stdlib + Streamlit yerleşikleri).

---

## 7. Kapsam dışı

| Şey | Neden |
|---|---|
| Çok kullanıcılı hesap/oturum yönetimi | Demo tek kullanıcılı; anahtarlar zaten oturumda |
| Anahtarların diske/keyring'e yazılması | Kullanıcı kararı: yalnız oturum belleği |
| LLM-as-judge kalite puanlaması | Non-deterministik; deterministik metrikler yeterli |
| Streaming (token token cevap akışı) | Metrik ve atıf post-check'i tam cevap ister; sonraki iş |
| Fiyatların otomatik güncellenmesi | Ağ bağımlılığı + kırılganlık; JSON elle güncellenir |
| Bölüm 2 (Satış Analizi) | Ayrı plan, bu genişletmeden sonra |

---

## 8. Riskler

| Risk | Etki | Azaltma |
|---|---|---|
| LangGraph migrasyonu güvenlik ağını bozar | **Yüksek** — sistem uydurmaya başlar | 7 agent testi değiştirilmeden geçmeli; ayrıca uçtan uca smoke test |
| Bağımlılık sayısı 15'e çıkıyor | Orta — kurulum ağırlaşır | Bulut SDK'ları isteğe bağlı `extras` yapılabilir; şimdilik zorunlu |
| Fiyat tablosu eskir | Orta — yanlış maliyet | JSON'da `_kaynak` ve tarih; arayüzde "fiyatlar elle güncellenir" notu |
| Anahtar sızıntısı (log/metrik) | **Yüksek** | Anahtar hiçbir yere yazılmaz; maskeleme testi |
| Bulut çağrıları para harcar | Orta | Değerlendirme sayfasında tahmini maliyet **çalıştırmadan önce** gösterilir + onay |
| Bölüm 2 daha da gecikir | Orta | Kullanıcı bilerek seçti; plan hazır bekliyor |

---

## 9. Kabul kriterleri

- [ ] Arayüzden Anthropic/OpenAI/Gemini anahtarı girilip model seçilebiliyor; anahtar diske yazılmıyor
- [ ] Yerel model arayüzden indirilip silinebiliyor, ilerleme görünüyor
- [ ] Her cevabın altında token / süre / maliyet görünüyor (fiyat yoksa "girilmedi")
- [ ] Metrik sayfasında model bazında karşılaştırma tablosu ve grafik var
- [ ] Değerlendirme sayfası ≥2 modeli sabit soru setiyle koşup tablo üretiyor
- [ ] **Mevcut 7 agent testi değiştirilmeden geçiyor** (LangGraph davranış sözleşmesi)
- [ ] `docker compose up` sonrası model elle çekilmeden sistem cevap veriyor
- [ ] Kalite kapısı: ruff temiz, kapsam ≥ %70, tüm testler yeşil
