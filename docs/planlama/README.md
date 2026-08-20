# AI Engineer Teknik Değerlendirme — Doküman Seti

Bu klasör, `AI Engineer/Ai engineer case study.pdf` dosyasındaki iki bölümlük teknik
değerlendirme için hazırlanan analiz, ürün gereksinimi (PRD), teknik tasarım (TRD) ve
adım adım uygulama planlarını içerir.

## Öncelik

1. **Bölüm 1 — RAG Tabanlı AI Agent** (zorunlu) → önce yapılacak
2. **Bölüm 2 — İlaç Sektörü Satış & Talep Analizi** (opsiyonel/bonus) → Bölüm 1 bittikten sonra

## Doküman Haritası

| Dosya | İçerik |
|---|---|
| [../Study-Case_Sunum.pptx](../Study-Case_Sunum.pptx) | Teknik sunum: RAG mimarisi, satış analizi ve Azure'a alınma süreci (22 slayt) |
| [../RAG_Ornek_soru-cevap_ciftleri.pdf](../RAG_Ornek_soru-cevap_ciftleri.pdf) | Örnek soru-cevap çiftleri, atıflarıyla birlikte |
| [00-case-analizi.md](00-case-analizi.md) | Case'in maddelenmiş özeti + gereksinim izlenebilirlik matrisi (her istenen madde → nerede karşılanıyor) |
| [01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md) | Her iki veri setinin gerçek ölçümlerle profillenmesi; tasarımı etkileyen kritik bulgular |
| [../raporlar/04-docker-uctan-uca-test-raporu.md](../raporlar/04-docker-uctan-uca-test-raporu.md) | Docker'da uçtan uca test raporu: her özelliğin teknolojisi, gerekçesi, çalışma biçimi ve ölçülmüş kanıtı; bulunan 3 kusur ve çözümleri |
| [02-karar-kaydi.md](02-karar-kaydi.md) | Teknoloji/model seçimlerinin gerekçeleri (ADR formatı) — case "kararların gerekçelendirilebilmesi" istiyor |
| [../bolum1-rag/PRD.md](../bolum1-rag/PRD.md) | RAG agent ürün gereksinimleri, kapsam, kabul kriterleri |
| [../bolum1-rag/TRD.md](../bolum1-rag/TRD.md) | RAG agent teknik tasarımı: mimari, modüller, veri modeli, algoritmalar |
| [../bolum2-analiz/PRD.md](../bolum2-analiz/PRD.md) | Analiz projesi gereksinimleri ve teslim kriterleri |
| [../bolum2-analiz/TRD.md](../bolum2-analiz/TRD.md) | Veri boru hattı, temizleme kuralları, metodoloji, modelleme tasarımı |

## 🚦 Uygulama Planı — Tek Kaynak

> ℹ️ **Bu klasör depoda yayımlanmıyor.** `docs/superpowers/` çalışma notlarıdır (plan ve spec dosyaları) ve `.gitignore`'dadır. Aşağıdaki dosya adları geçmişin nasıl yürütüldüğünü göstermek için bırakıldı; bağlantı verilmedi.

**Kod yazarken izlenen plan yalnızca buydu:**

| Dosya | İçerik |
|---|---|
| `superpowers/plans/rag-agent/00-overview.md` | Bölüm 1'in amacı, global kısıtlar, 14 task'ın sırası ve bağımlılık zinciri |
| `superpowers/plans/rag-agent/` | Task 01–14: her biri kendi testi, kodu, komutu ve beklenen çıktısıyla bağımsız (111–303 satır) |
| `superpowers/plans/rag-agent/99-verification-checklist.md` | Teslim öncesi final kabul listesi |

**Okuma kuralı:** `00-overview.md` + **tek** task dosyası. Tüm task seti asla birlikte okunmaz.

> Bölüm 2'nin superpowers planı, Bölüm 1 tamamlandıktan sonra yazılacak
> (eşik kalibrasyonu gibi henüz bilinmeyen çıktılara dayanmaması için).

### Eski faz planları (kavramsal arka plan)

| Dosya | Durum |
|---|---|
| [../bolum1-rag/UYGULAMA-PLANI.md](../bolum1-rag/UYGULAMA-PLANI.md) | ⚠️ **Uygulanmaz.** Faz anlatısı ve gerekçe için referans; adım numaraları superpowers task'ları tarafından geçersiz kılındı |
| [../bolum2-analiz/UYGULAMA-PLANI.md](../bolum2-analiz/UYGULAMA-PLANI.md) | ⚠️ Aynı — Bölüm 2 için task planı yazılınca geçersiz kalacak |

## Temel Prensip

Case metni şunu söylüyor: *"Önemli olan son ürünün çalışır olması ve kararların
gerekçelendirilebilmesidir."* Bu doküman setinin tamamı **demo seviyesi** hedefler:
dokümanda yazan zorunlu + bonus özellikler eksiksiz çalışsın, fazlası eklenmesin.
Kapsam dışı bırakılan her şey ilgili PRD'nin "Kapsam Dışı" bölümünde açıkça listelendi.
