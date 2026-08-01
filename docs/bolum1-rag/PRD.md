# PRD — Bölüm 1: RAG Tabanlı AI Agent

**Durum:** Plan · **Öncelik:** 1 (Bölüm 2'den önce) · **Hedef:** Çalışır demo prototipi

---

## 1. Problem ve Amaç

Bir şirketin iç bilgi tabanı (İK politikaları, araç prosedürleri, çalışan SSS, ürün
taksonomisi, ilaç KÜB dokümanları) büyüdükçe çalışanlar doğru bilgiye ulaşamıyor.

**Amaç:** Lokal ortamda çalışabilen, RAG mimarisi kullanan bir soru-cevap agent'ı
prototipi. Kullanıcı Türkçe doğal dilde soru sorar; sistem ilgili doküman parçalarını
bulur, LLM'e iletir ve **hangi belgeden/bölümden** geldiğini göstererek cevaplar.

**Bu bir demodur.** Hedef, case dokümanındaki zorunlu ve bonus özelliklerin **eksiksiz ve
çalışır** olması. Bunun ötesinde özellik eklenmeyecek.

---

## 2. Kullanıcı ve Senaryolar

**Birincil kullanıcı:** Şirket çalışanı (teknik olmayan). **İkincil:** Case'i değerlendiren
mühendis — sistemin nasıl çalıştığını inceleyecek.

### Kullanıcı Hikâyeleri

| ID | Hikâye | Kabul Kriteri |
|---|---|---|
| US-1 | Çalışan olarak İK politikası hakkında Türkçe soru sormak istiyorum | "Yıllık izin talebimi nasıl yaparım?" → HRPortal adımlarını içeren cevap + kaynak |
| US-2 | Cevabın nereden geldiğini görmek istiyorum ki güvenebileyim | Her cevapta `[dosya adı — bölüm/sayfa]` formatında ≥1 atıf |
| US-3 | Tablodaki bilgiyi de sorabilmek istiyorum | "Direktör seviyesinin aylık yakıt limiti nedir?" → `1.500 TL/ay` (DOCX tablosundan) |
| US-4 | İlaç KÜB'ünde belirli bir bölümü sorabilmek istiyorum | "Aksef'in kontrendikasyonları neler?" → Bölüm 4.3 atfıyla cevap |
| US-5 | Sistemin bilmediğinde uydurmamasını istiyorum | Belgede olmayan soru → "Bilgi tabanımda bu bilgi yok" (uydurma yok) |
| US-6 | Alakasız soruda kibar bir red istiyorum | "Bugün hava nasıl?" → kibar red + kapsam açıklaması |
| US-7 | Terminal yerine görsel arayüz istiyorum | Streamlit'te soru kutusu + cevap + kaynak paneli |
| US-8 | Değerlendiren olarak 3 komutla çalıştırmak istiyorum | README'deki 3 komut temiz ortamda çalışır |

---

## 3. Kapsam

### 3.1 Kapsam İçi — Zorunlu (case §1.3)

- **F1.** Türkçe doğal dilde soru girişi (CLI + Streamlit).
- **F2.** 6 kaynak belgenin indekslenmesi (2 PDF, 2 DOCX, 2 XLSX).
- **F3.** Soruya en ilgili doküman parçalarının bulunup LLM'e iletilmesi.
- **F4.** Cevapta kaynak gösterimi: **dosya adı + bölüm + (varsa) sayfa numarası**.
- **F5.** En az 1 tool entegrasyonu → 3 tool: `search_documents`, `lookup_section`,
  `list_documents`.
- **F6.** LLM entegrasyonu, tercihin README'de gerekçelendirilmesi.

### 3.2 Kapsam İçi — Bonus (case §1.3, hepsi dahil)

- **F7.** "Bilmiyorum" yönetimi — hallucination üretmeden bilgi yokluğunu bildirme.
- **F8.** Konu dışı filtresi — alakasız soruların kibarca reddi.
- **F9.** Streamlit arayüzü.
- **F10.** Çoklu belge formatı desteği (DOCX + XLSX + PDF).
- **F11.** `docker-compose` ile tek komutla ayağa kalkma.

### 3.3 Kapsam Dışı (bilinçli olarak yapılmayacak)

| Özellik | Neden dışarıda |
|---|---|
| Kullanıcı yönetimi / kimlik doğrulama | Case istemiyor; tek kullanıcılı demo |
| Sohbet geçmişi kalıcılığı, çok turlu bağlam takibi | Case tek soru-cevap senaryosu tanımlıyor. Streamlit oturum içi geçmiş gösterir ama diske yazılmaz |
| Cross-encoder reranker | Bu korpus boyutunda ölçülebilir fayda yok, +1 model indirmesi (ADR-004) |
| Query rewriting / HyDE / çok adımlı planlama | Demo kapsamını aşar; basit tool döngüsü yeterli |
| OCR (taranmış PDF) | Her iki PDF de metin katmanlı — ölçüldü (24k/57k karakter çıkarılabiliyor) |
| Otomatik yeniden indeksleme / dosya izleme | `ingest.py` elle çalıştırılır |
| Değerlendirme harness'ı (RAGAS vb.) | Demo notebook'undaki 8 senaryo yeterli kanıt |
| Streaming cevap | Görsel iyileştirme; işlevsel katkısı yok |
| Çok dilli destek | Korpus tamamen Türkçe |

---

## 4. Fonksiyonel Gereksinimler (detay)

### FR-1 Doküman Yükleme (Ingest)
- `data/` altındaki tüm desteklenen dosyalar `glob` ile taranır (dosya adları koda gömülmez —
  bkz. bulgular §1.6, dosya adında Türkçe `ı` var).
- PDF → bölüm + sayfa metadata'sı; DOCX → başlık hiyerarşisi + **tablolar**; XLSX → satır bazlı kayıt.
- Çıktı: chunk listesi + Chroma koleksiyonu + BM25 indeksi, `storage/` altında kalıcı.
- Idempotent: aynı komut tekrar çalıştırıldığında koleksiyon sıfırlanıp yeniden kurulur.

### FR-2 Retrieval
- Hibrit: BM25 (leksik) + dense (semantik), RRF ile birleştirme.
- Türkçe normalizasyon: sorgu ve indeks tarafında ASCII katlama (bulgular §1.4).
- `top_k` varsayılan 5, `source_filter` ile belge kısıtı desteği.
- Dönen her sonuç metadata'sını (dosya, bölüm, sayfa) taşır.

### FR-3 Agent Döngüsü
- LLM tool-calling ile: soru → tool çağrısı → sonuç → (gerekirse ikinci çağrı) → nihai cevap.
- Maksimum 3 tool çağrısı (sonsuz döngü koruması).
- Tool çağrıları ve sonuçları izlenebilir (trace) — demo notebook'unda ve Streamlit'te gösterilir.

### FR-4 Kaynak Gösterimi
- Format: `[dosya adı — Bölüm X.Y Başlık, s.N]`
  - PDF örn: `[Aksef 500 mg FKTB_Onaylı KUB.pdf — Bölüm 4.2 Pozoloji ve uygulama şekli, s.2]`
  - DOCX örn: `[arac_kullanim_proseduru.docx — 3. ARAÇ TAHSİS POLİTİKASI]`
  - XLSX örn: `[calisan_sss_rehberi.xlsx — Genel SSS, satır 5]`
- Cevabın altında kullanılan kaynakların listesi ayrıca gösterilir.

### FR-5 Güvenlik Ağı (bilmiyorum + konu dışı)
- Katman 1: retrieval skoru eşik altındaysa LLM'e gidilmez.
- Katman 2: grounded sistem promptu.
- Katman 3: cevapta geçerli atıf yoksa cevap reddedilir.
- (ADR-008)

### FR-6 Arayüzler
- **CLI:** `python -m src.rag.cli "soru"` ve interaktif mod.
- **Streamlit:** soru kutusu, cevap, genişletilebilir "Kaynaklar" paneli, "Tool izleri" paneli,
  yan panelde provider/top_k ayarı.

---

## 5. Fonksiyonel Olmayan Gereksinimler

| # | Gereksinim | Hedef |
|---|---|---|
| NFR-1 | Kurulum | README'deki **3 komut** temiz bir ortamda çalışmalı |
| NFR-2 | İlk ingest süresi | < 3 dakika (model indirme hariç) |
| NFR-3 | Sorgu yanıt süresi | Retrieval < 500 ms; toplam LLM dahil < 15 sn (lokal), < 5 sn (bulut) |
| NFR-4 | Offline çalışma | İndeksleme ve arama internet olmadan çalışır (embedding lokal) |
| NFR-5 | Platform | Windows + Linux; Docker ile platform bağımsız |
| NFR-6 | Kodlama | Tüm I/O UTF-8; Windows konsolunda Türkçe çıktı bozulmaz |
| NFR-7 | Bağımlılık | requirements.txt sürüm pinli, ≤ 12 doğrudan bağımlılık |

---

## 6. Kabul Kriterleri (teslim öncesi kontrol listesi)

- [ ] `pip install -r requirements.txt` temiz venv'de hatasız tamamlanır
- [ ] `python scripts/ingest.py` 6 belgeyi de işler, chunk sayısını raporlar, hata vermez
- [ ] `streamlit run app.py` arayüzü açar ve soru cevaplar
- [ ] Demo notebook'unda **≥5** (planlanan 8) soru-cevap çifti, hepsinde kaynak gösterimi
- [ ] En az **1** "bilmiyorum" senaryosu (planlanan 2: belgede yok + konu dışı)
- [ ] Her belge formatından (PDF/DOCX/XLSX) en az 1 soru cevaplanmış
- [ ] En az 1 soru **DOCX tablosundan** cevaplanmış (tablo desteğinin kanıtı)
- [ ] Tool çağrı izi (trace) demo'da görünür — tool entegrasyonunun kanıtı
- [ ] README: ASCII mimari diyagramı, model/framework gerekçeleri, karşılaşılan zorluklar,
      sınırlılıklar ve iyileştirme önerileri
- [ ] `docker compose up` ile sistem tek komutla ayağa kalkar

---

## 7. Demo Soru Seti (planlanan 8 senaryo)

| # | Soru | Hedef kaynak | Neyi kanıtlıyor |
|---|---|---|---|
| 1 | Yıllık izin talebimi nasıl yaparım? | `calisan_sss_rehberi.xlsx` / `ik_surecleri_politikası.docx` | XLSX okuma + çoklu kaynak |
| 2 | İşe alım süreci kaç aşamadan oluşur? | `ik_surecleri_politikası.docx` §2.3 | DOCX başlık hiyerarşisi |
| 3 | Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir? | `arac_kullanim_proseduru.docx` tablo | **DOCX tablo desteği** |
| 4 | Havuz aracı nasıl talep edilir? | `arac_kullanim_proseduru.docx` §4.1 | Prosedür adımları |
| 5 | Aksef 500 mg'ın kontrendikasyonları nelerdir? | `Aksef ... KUB.pdf` Bölüm 4.3 | **PDF bölüm + sayfa atfı** |
| 6 | Duxet'in gebelikte kullanımı hakkında ne yazıyor? | `Duxet ... KUB.pdf` Bölüm 4.6 | Çok sayfalı PDF'te doğru bölüm |
| 7 | Vitatin95 ürününün terapötik sistemi ve ürün müdürü kim? | `Anonim_Urun_Taksonomi_100Satir.xlsx` | Yapılandırılmış satır retrieval |
| 8a | Şirketin 2027 yılı kâr hedefi nedir? | — | **"Bilmiyorum"** (alan içi, belgede yok) |
| 8b | Bugün hava nasıl olacak? | — | **Konu dışı filtresi** |

---

## 8. Riskler

| Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|
| Lokal LLM tool-calling'i tutarsız üretiyor | Orta | Yüksek | Provider soyutlaması (ADR-007); bulut fallback; tool şeması basit tutulur |
| Türkçe karakter tutarsızlığı retrieval'ı bozuyor | **Yüksek** (ölçüldü) | Yüksek | ASCII katlama + hibrit arama (ADR-004) — plana gömüldü |
| Embedding modeli indirmesi (~1,1 GB) demoda gecikme yaratıyor | Orta | Orta | Docker build'de önceden çekilir; README'de uyarı |
| PDF bölüm tespitinde yanlış pozitif (Duxet s.15 dipnotları) | Orta | Düşük | KÜB bölüm beyaz listesi + monoton artış kontrolü |
| "Bilmiyorum" eşiği çok agresif → geçerli sorulara da red | Orta | Orta | Eşik demo notebook'unda kalibre edilir, README'de raporlanır |
| DOCX tabloları kaçırılırsa US-3 çalışmaz | Yüksek (varsayılan davranış) | Yüksek | Loader'da tablo çıkarımı zorunlu adım; test ile doğrulanır |
