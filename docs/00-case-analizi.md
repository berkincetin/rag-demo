# Case Analizi ve Gereksinim İzlenebilirlik Matrisi

Kaynak: `AI Engineer/Ai engineer case study.pdf` (4 sayfa)

---

## 1. Case'in Yapısı

| Bölüm | Zorunluluk | Konu | Teslim Formatı |
|---|---|---|---|
| Bölüm 1 | **Zorunlu** | Lokal çalışabilen RAG tabanlı soru-cevap agent'ı | Çalışır Python kodu (ZIP) + README + demo |
| Bölüm 2 | Opsiyonel/Bonus | İlaç sektörü satış & talep analizi (4 pazar, 124 ay) | Jupyter Notebook + görseller + yorumlar |

Case'in kendi ifadesi: *"Belgelerin içeriği değil, sisteminizin bu belgeler üzerinde nasıl
çalıştığı değerlendirilecektir."* → Değerlendirme kriteri **sistem davranışı**, belge
bilgisinin doğruluğu değil. Bu, tasarımı doğrudan etkiliyor: kaynak gösterimi, "bilmiyorum"
davranışı ve farklı formatların (PDF/DOCX/XLSX) tutarlı işlenmesi, cevap kalitesinden daha
yüksek öncelikli.

---

## 2. Bölüm 1 — Gereksinim Matrisi

### 2.1 Zorunlu Özellikler

| # | Case Maddesi | Karşılanma Yeri | Doğrulama |
|---|---|---|---|
| Z1 | Kullanıcı doğal dilde soru sorabilmeli | CLI (`src/rag/cli.py`) + Streamlit (`app.py`) | Demo notebook 5+ soru |
| Z2 | Sisteme sorulan soruya en ilgili doküman parçalarını bulup LLM'e iletmeli | Hibrit retriever (`retriever.py`) → agent context | Notebook'ta retrieved chunk dökümü |
| Z3 | Cevapta hangi belgeden (dosya adı veya bölüm) bilgi alındığını göstermeli | Zorunlu atıf formatı + post-check | Her cevapta `[dosya — bölüm, s.N]` |
| Z4 | En az 1 tool/araç entegrasyonu (`search_documents`, `lookup_section` gibi) | 3 tool: `search_documents`, `lookup_section`, `list_documents` | Notebook'ta tool-call trace |
| Z5 | LLM entegrasyonu; lokal tercih edilir, bulut kabul; **tercih README'de gerekçelendirilmeli** | `llm.py` provider soyutlaması + [02-karar-kaydi.md](02-karar-kaydi.md) | README "Model Seçimi" bölümü |

### 2.2 Bonus Özellikler

| # | Case Maddesi | Planlanan Karşılık | Zorluk |
|---|---|---|---|
| B1 | 'Bilmiyorum' yönetimi (hallucination yok) | Skor eşiği + grounded-prompt + atıf post-check (3 katmanlı) | Orta |
| B2 | Konu dışı filtresi (kibar red) | Retrieval skor kapısı + sistem promptu kural | Düşük |
| B3 | Streamlit/Gradio arayüzü | Streamlit (kaynak paneli + tool trace görünümü) | Düşük |
| B4 | Çoklu belge desteği (DOCX/XLSX okuma) | 3 loader: PDF, DOCX (tablo dahil), XLSX (3 sayfalı SSS + taksonomi) | Orta |
| B5 | Docker / docker-compose ile tek komut | `Dockerfile` + `docker-compose.yml` (app + opsiyonel ollama servisi) | Düşük |

**Tüm bonuslar plana dahil.** Gerekçe: 5 bonusun 4'ü zaten zorunlu özelliklerin doğal
uzantısı (B4 veri setinin kendisi tarafından dayatılıyor — 6 belgenin 3'ü DOCX/XLSX).

### 2.3 Teslim Edilecekler

| Teslim | Case Şartı | Plan |
|---|---|---|
| Kod reposu | Çalışır Python kodu (ZIP) | `src/` + `app.py` + `scripts/` |
| requirements.txt | Zorunlu | Sürüm pinli |
| README.md | Kurulum **3 komutla** başlamalı | `pip install -r requirements.txt` → `python scripts/ingest.py` → `streamlit run app.py` |
| Demo | **En az 5** örnek soru-cevap çifti | `notebooks/demo.ipynb` — 8 soru planlandı |
| Demo | Her cevapta kaynak: dosya adı, bölüm veya sayfa no | Atıf formatı zorunlu |
| Demo | **1 adet 'bilmiyorum' senaryosu** | 2 senaryo: (a) alan içi ama belgede yok, (b) tamamen konu dışı |
| Açıklama dokümanı | Mimari diyagramı (görsel veya ASCII) | README'de ASCII diyagram |
| Açıklama dokümanı | Framework ve model seçim gerekçeleri | [02-karar-kaydi.md](02-karar-kaydi.md) → README özeti |
| Açıklama dokümanı | Karşılaşılan zorluklar ve çözüm yaklaşımı | README (bulgular [01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md) dosyasından beslenecek) |
| Açıklama dokümanı | Sınırlılıklar ve iyileştirme önerileri | README son bölüm |

---

## 3. Bölüm 2 — Gereksinim Matrisi

| # | Analiz Görevi | Ana Çıktı | Kritik Not |
|---|---|---|---|
| A1 | Pazarlar genelinde aylık satış performansı ve ürün kırılımı (son 2 yıl, Brüt Kutu + Net TL) | Pazar başına zaman serisi + ürün konsantrasyonu (Pareto) | Son 2 yıl = 2024-05 … 2026-04 |
| A2 | Pazar yapısı ve rekabet pozisyonu (Şirket 1/2/Diğer pazar payı, 2016→bugün) | Yığılmış pay grafiği + HHI | Pay = Brüt Kutu % |
| A3 | Mevsimsellik indeksi (ürün × pazar) | Isı haritası + mevsimsellik gücü metriği | Kısa seriler hariç tutulacak |
| A4 | MF Oranı'nın satışa etkisi (MF > %10 → t+1) | Olay çalışması + istatistiksel test tablosu | **MF ölçek hatası önce düzeltilmeli** (bkz. bulgular) |
| A5 | Rakip karşılaştırması ve büyüme dinamikleri (YoY, Şirket 1 vs 2) | Büyüme tablosu + rekabet yoğunluğu | Diğer Şirket hacim kaybı kanıtlanmalı |
| A6 | Birim fiyat trendi ve promosyon maliyeti | Fiyat trendi + MF gelir kaybı TL hesabı | Birim Fiyat = Net TL / Net Kutu |
| A7 | Bir sonraki ay Brüt Kutu tahmini, **en az 2 yaklaşım** (naive + ML) | Pazar bazında MAE/MAPE/RMSE tablosu + MF ablasyonu | Şirket 1'in 18 ürün-pazar serisi |

### Teslim Edilecekler — Bölüm 2

| Teslim | Case Şartı |
|---|---|
| Jupyter Notebook (.ipynb) | Tüm analizler ve görseller |
| Görseller | Her soru için **en az 1** grafik |
| Yorum | Her sorunun altında **hem teknik hem iş** açısından yorum |
| Model karşılaştırması (Soru 7) | MAE, MAPE, RMSE — **pazar bazında** tablo |

---

## 4. Case'ten Çıkarılan Örtük Gereksinimler

Doküman metninde açıkça yazmıyor ama değerlendirmeyi doğrudan etkileyen maddeler:

1. **Türkçe dil desteği.** Tüm korpus Türkçe; üstelik DOCX dosyaları ASCII'ye indirgenmiş
   ("Insan Kaynaklari"), PDF'ler tam Türkçe karakterli ("İnsan Kaynakları"). Aynı sorunun
   iki belgeyi de bulabilmesi için normalizasyon şart. → [01-veri-kesif-bulgulari.md](01-veri-kesif-bulgulari.md) §2.4
2. **"Lokal ortamda çalışabilen"** ifadesi Bölüm 1.1'de geçiyor. Sistem internet olmadan da
   indeksleme + arama yapabilmeli; sadece LLM çağrısı bulut olabilir. → Embedding modeli lokal seçildi.
3. **Reprodüksiyon.** "3 komutla başlamalı" şartı, indeksin repoda commit'li olmasını değil,
   ingest komutunun deterministik çalışmasını gerektiriyor.
4. **Gerekçelendirme.** Her iki bölümde de "kararların gerekçelendirilmesi" açık kriter.
   Bu yüzden ayrı bir karar kaydı (ADR) dosyası tutuluyor.
