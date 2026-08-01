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
| [00-case-analizi.md](00-case-analizi.md) | Case'in maddelenmiş özeti + gereksinim izlenebilirlik matrisi (her istenen madde → nerede karşılanıyor) |
| [01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md) | Her iki veri setinin gerçek ölçümlerle profillenmesi; tasarımı etkileyen kritik bulgular |
| [02-karar-kaydi.md](02-karar-kaydi.md) | Teknoloji/model seçimlerinin gerekçeleri (ADR formatı) — case "kararların gerekçelendirilebilmesi" istiyor |
| [bolum1-rag/PRD.md](bolum1-rag/PRD.md) | RAG agent ürün gereksinimleri, kapsam, kabul kriterleri |
| [bolum1-rag/TRD.md](bolum1-rag/TRD.md) | RAG agent teknik tasarımı: mimari, modüller, veri modeli, algoritmalar |
| [bolum1-rag/UYGULAMA-PLANI.md](bolum1-rag/UYGULAMA-PLANI.md) | Faz faz, adım adım yapılacaklar + her adımın "bitti" tanımı |
| [bolum2-analiz/PRD.md](bolum2-analiz/PRD.md) | Analiz projesi gereksinimleri ve teslim kriterleri |
| [bolum2-analiz/TRD.md](bolum2-analiz/TRD.md) | Veri boru hattı, temizleme kuralları, metodoloji, modelleme tasarımı |
| [bolum2-analiz/UYGULAMA-PLANI.md](bolum2-analiz/UYGULAMA-PLANI.md) | 7 analiz görevinin adım adım uygulama planı |

## Temel Prensip

Case metni şunu söylüyor: *"Önemli olan son ürünün çalışır olması ve kararların
gerekçelendirilebilmesidir."* Bu doküman setinin tamamı **demo seviyesi** hedefler:
dokümanda yazan zorunlu + bonus özellikler eksiksiz çalışsın, fazlası eklenmesin.
Kapsam dışı bırakılan her şey ilgili PRD'nin "Kapsam Dışı" bölümünde açıkça listelendi.
