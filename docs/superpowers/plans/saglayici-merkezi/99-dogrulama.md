# Doğrulama Listesi — Sağlayıcı Merkezi

> Task 13'ten sonra çalıştırılır. Kabul kriterleri:
> [tasarım dokümanı §9](../../specs/2026-08-02-saglayici-merkezi-tasarim.md).

## Davranış sözleşmesi (en kritik)

- [ ] `git diff --stat tests/test_agent.py` **boş** — dosya hiç değiştirilmedi
- [ ] `pytest tests/test_agent.py -v` → **7 passed**
- [ ] `python scripts/smoke_test.py` → **Başarısız kontrol sayısı: 0**
- [ ] Konu dışı soru hâlâ LLM çağrılmadan reddediliyor (tool izi boş)
- [ ] Atıfsız cevap hâlâ bir kez onarılıyor, sonra "bilgi bulamadım" oluyor

## Sağlayıcı ve model seçimi

- [ ] Anahtar girilmeden yalnız yerel modeller seçilebiliyor
- [ ] Anthropic / OpenAI / Gemini anahtarı girilince ilgili modeller listeye giriyor
- [ ] Anahtar ekranda maskeli, sayfa yenilenince kayboluyor
- [ ] `grep -ri "sk-" storage/ config/ *.json` → **anahtar bulunmuyor**
- [ ] Metrik veritabanında anahtar sütunu/değeri yok

## Yerel model yönetimi

- [ ] Yüklü modeller boyutlarıyla listeleniyor
- [ ] Küçük bir model arayüzden indirildi, ilerleme çubuğu ilerledi
- [ ] İndirilen model Sağlayıcılar sayfasında seçilebiliyor
- [ ] Ollama kapalıyken sayfa çökmüyor, açıklayıcı mesaj veriyor

## Metrikler ve maliyet

- [ ] Her cevabın altında süre / token / maliyet görünüyor
- [ ] Fiyatı bilinmeyen model **"fiyat girilmedi"** diyor, `$0` **demiyor**
- [ ] Ölçülemeyen token NULL, `0` değil
- [ ] Metrik sayfasında model bazında karşılaştırma tablosu ve grafik var
- [ ] Kısmi fiyatlandırma açıkça işaretli (`2/4 koşu`)
- [ ] Reddedilen sorular da kaydediliyor (kapı isabeti ölçülebiliyor)

## Değerlendirme

- [ ] ≥2 model sabit soru setiyle koşuldu, karşılaştırma tablosu üretildi
- [ ] Onay kutusu işaretlenmeden çalıştırma mümkün değil
- [ ] Tahmini maliyet çalıştırmadan önce gösterildi
- [ ] Ölçülemeyen oran `—` gösteriliyor, `0` değil
- [ ] Taban çizgisi MEMORY.md'ye yazıldı

## Kurulum ve Docker

- [ ] `docker compose down -v && docker compose up --build` sonrası **elle pull olmadan**
      smoke test 0 hata
- [ ] `python scripts/setup.py` Ollama yoksa kurulum komutunu gösteriyor, **kurmuyor**
- [ ] Kuantize sonekli model kurulu sayılıyor (gereksiz 4,7 GB indirme yok)

## Kalite kapısı

- [ ] `ruff format .` değişiklik yok
- [ ] `ruff check .` temiz
- [ ] `pytest -q --cov --cov-fail-under=70` yeşil
- [ ] Çalışma zamanı bağımlılığı **15** (overview'daki yeni sınır)

## Dokümantasyon

- [ ] ADR-011 (LangGraph), ADR-012 (oturum anahtarları), ADR-013 (fiyat tablosu) yazıldı
- [ ] ADR-001 "superseded by ADR-011" olarak işaretlendi
- [ ] README dört yeni bölümü içeriyor
- [ ] README'de iki güvenlik notu var: anahtarlar diske yazılmaz · sorular metriğe yazılır
- [ ] PROGRESSION.md ve MEMORY.md güncel

## Sonraki adım

- [ ] **Bölüm 2 (Satış Analizi) hâlâ başlamadı** — bu genişletme bittiğinde sıradaki iş odur
