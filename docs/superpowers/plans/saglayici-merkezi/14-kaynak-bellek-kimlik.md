# Task 14–17: Kaynak ölçümü, sohbet belleği ve kullanıcı kimliği

> [00-overview.md](00-overview.md) — global kısıtlar geçerli.
> **Önceki:** [Task 13](13-kurulum-docker-docs.md) · Kullanıcı isteği: 2026-08-03

Dört yeni yetenek. Task 1–13 tamamlandıktan sonra bu sırayla uygulanır.

## Mevcut durum tespiti

| İstek | Şu an var mı? |
|---|---|
| Yerel modelde CPU/RAM/GPU tüketimi | ❌ **Yok** — hiç ölçülmüyor |
| Giriş/çıkış token'ı ayrı ayrı | ⚠️ **Kısmen** — `2834→93` biçiminde birlikte; metrik tablosunda ayrı sütun yok |
| Sohbet belleği (memory) | ❌ **Yok** — her soru tamamen bağımsız, önceki soru hatırlanmıyor |
| Kullanıcı adı alanı | ❌ **Yok** |

---

## Task 14 — Kaynak tüketimi ölçümü

**Dosyalar:** `src/rag/resources.py` (yeni) · **Test:** `tests/test_resources.py`
**Yeni bağımlılık:** `psutil` (16 → çalışma zamanı bağımlılığı)

**Üretir:** `ResourceSnapshot(cpu_percent, ram_used_mb, ram_total_mb, gpu_used_mb, gpu_total_mb)`,
`sample_resources()`, `ResourceMonitor` (bir çağrı boyunca **tepe** değerleri toplar)

### Nasıl ölçülür

| Kaynak | Kaynak yeri | Not |
|---|---|---|
| CPU % | `psutil.cpu_percent(interval=None)` | Sistem geneli; Ollama ayrı süreçte çalıştığı için tek süreç yetmez |
| RAM | `psutil.virtual_memory()` | Kullanılan/toplam MB |
| GPU | Ollama `/api/ps` → `size_vram` | **En güvenilir sinyal:** `size_vram == 0` ⇒ model CPU'da. `nvidia-smi` yoksa `None` |

🚨 **Ölçülemeyen `None` kalır.** GPU yoksa `0` **yazılmaz** — "GPU yok" ile "GPU var ama
kullanılmıyor" farklı şeyler.

`ResourceMonitor` bir arka plan iş parçacığında ~1 sn aralıkla örnekler; `answer()` boyunca
**tepe CPU** ve **tepe RAM** kaydedilir (ortalama değil — darboğaz tepe değerde görünür).

### Metrik şemasına eklenenler
`peak_cpu_percent`, `peak_ram_mb`, `gpu_vram_mb` sütunları (hepsi NULL olabilir).
Mevcut satırlar için NULL kalır — şema `ALTER TABLE … ADD COLUMN` ile göçürülür.

### DoD
- [x] GPU yoksa `gpu_used_mb is None` (0 değil) — `test_gpu_distinguishes_unmeasured_from_cpu_bound`
- [x] `size_vram == 0` iken "CPU'da çalışıyor" olarak raporlanıyor — `format_gpu(0)`
- [x] Monitor iş parçacığı `answer()` bitince **durduruluyor** (sızıntı testi)
- [x] Eski metrik veritabanı yeni sütunlarla açılabiliyor — `test_an_older_database_is_migrated_in_place`

---

## Task 15 — Token'ları ayrı ayrı göster

**Dosyalar:** `pages/3_Metrikler.py`, `src/rag/ui_state.py` · **Test:** `tests/test_ui_state.py`

Küçük ama net iş: metrik tablosunda `giriş token` ve `çıkış token` **ayrı sütunlar**;
özet tablosunda model başına **toplam giriş** / **toplam çıkış** ve `ort. giriş/soru`.
Sohbet rozetinde de `↑2834 / ↓93` biçimi (yön okları anlamı netleştirir).

Ayrıca kaynak sütunları: `tepe CPU %`, `tepe RAM`, `GPU VRAM`.

### DoD
- [x] Giriş ve çıkış ayrı sütun; ölçülmeyen `—` — `test_unmeasured_token_totals_show_a_dash`
- [x] Özet tablosunda model başına toplam giriş/çıkış
- [x] `summary_by_model()` bu toplamları döndürüyor — `test_summary_totals_input_and_output_tokens_separately`

---

## Task 16 — Sohbet belleği (session memory) 🎯

**Dosyalar:** `src/rag/memory.py` (yeni), `src/rag/graph.py`, `app.py`
**Test:** `tests/test_memory.py`, `tests/test_graph.py` (genişler)

**Üretir:** `ConversationMemory(max_turns=5)` — `add(question, answer)`, `recent_turns()`,
`clear()`; grafiğe `history` girdisi.

### 🚨 Tasarım riski: skor kapısı takip sorusunu eler

Bu, işin en kritik noktası. Şu an 1. katman **yalnız sorunun kendisiyle** retrieval yapıyor.
Bellek eklenince kullanıcı *"peki müdür seviyesinde ne kadar?"* diye sorabilir — bu metin
tek başına hiçbir belgeye benzemez, kapı onu **konu dışı sayıp reddeder**. Yani bellek
eklemek, düzgün yapılmazsa **mevcut doğru davranışı bozar**.

**Çözüm:** kapıya giden sorgu, son kullanıcı sorusuyla **zenginleştirilir**:
`f"{son_soru} {yeni_soru}"` — yalnız **retrieval** için. LLM'e giden mesajlarda tam geçmiş
ayrıca yer alır. Böylece takip sorusu doğru belgeleri bulur, kapı isabeti korunur.

### Kapsam sınırı
- Bellek **oturum içi**; diske yazılmaz (anahtarlarla aynı gerekçe)
- Son **5 tur** tutulur (bağlam şişmesin; 7B modelde uzun bağlam zaten yavaş)
- "Sohbeti temizle" düğmesi
- Metrik kaydına `turn_index` eklenir (kaçıncı tur olduğu ölçülebilsin)

### Uygulama sırasında eklenen: ekran dökümü ayrı tutuluyor

Reddedilen cevaplar **belleğe girmiyor** (bir sonraki arama sorgusunu kirletirlerdi) ama
kullanıcı onları ekranda görmeli. Bu yüzden `ui_state` ayrı bir `transcript` listesi
tutuyor: modelin hatırladığının üst kümesi.

Ayrıca `st.text_input` değerini rerun'lar arasında koruduğu için kenar çubuğundaki her
tıklama **aynı soruyu yeniden cevaplatıyor** ve belleğe ikinci bir tur ekliyordu.
`st.chat_input`'a geçildi: metni yalnız gönderimden sonraki koşuda bir kez döndürür.

### DoD
- [x] Takip sorusu (`"peki ya X?"`) doğru belgeyi buluyor — `test_the_enriched_follow_up_finds_the_vehicle_procedure` (entegrasyon). Kontrolü: `test_a_bare_follow_up_question_would_be_refused` çıplak sorunun reddedildiğini gösteriyor.
  **Arayüzde uçtan uca doğrulandı:** *"Direktör … yakıt limiti nedir?"* → `1.500 TL/ay`,
  ardından *"peki ya müdür seviyesinde?"* → `1.000 TL/ay` (kaynak belgedeki tabloyla
  birebir), `gate_passed=1`, `turn_index=1`, atıf 1, 306,0 sn
- [x] Bellek kapalıyken davranış birebir eskisi gibi (8 agent testi yeşil)
- [x] 5 turdan eskisi düşüyor — `test_only_the_last_n_turns_are_kept`
- [x] "Sohbeti temizle" belleği sıfırlıyor — `test_clearing_the_chat_empties_the_transcript_and_the_memory`
- [x] Bellek diske yazılmıyor — `test_memory_module_never_writes_to_disk`

---

## Task 17 — Kullanıcı adı ve kişiselleştirme

**Dosyalar:** `src/rag/ui_state.py`, `src/rag/prompts.py`, `src/rag/graph.py`, `app.py`
**Test:** `tests/test_ui_state.py`, `tests/test_graph.py`

Kullanıcı adı oturumda tutulur ve sistem promptuna **tek kısa cümle** olarak eklenir:

```
Kullanıcının adı: {ad}. Uygun olduğunda ona adıyla hitap et.
```

### Uygulama sırasında ölçülen: sistem promptu tek başına yetmedi

Beklenen risk (tool çağrısının bastırılması) **gerçekleşmedi** — `smoke_test.py "Berkin"`
0 hata verdi, üç alan içi soruda da `tool=1`. Ama **başka bir şey** çıktı: isim yalnız
sistem promptundayken model onu **hiç kullanmadı** (iki ayrı temellendirilmiş cevap,
ikisinde de isim geçmedi). Yani özellik bozulmadı, sadece **etkisizdi**.

Bu yüzden aşağıdaki "bozulursa" planı, farklı bir sebeple de olsa uygulandı: isim
`CITATION_REMINDER` ile birlikte **tool sonucu mesajına** da ekleniyor. Task 12'de atıf
kuralı için ölçülen aynı davranış: 7B model sistem promptundaki talimatı görmezden
geliyor, tool sonucuna iliştirileni uyguluyor.

### 🚨 Ölçülmüş risk: sistem promptu uzatmak tool çağrısını bastırıyor

MEMORY.md Task 12'de ölçüldü: qwen2.5-7b'de sistem promptuna eklenen **her** fazladan cümle
tool çağrısını bastırabiliyor. Bu yüzden:
- İsim satırı **tek cümle** ve promptun **sonuna** eklenir
- İsim boşsa satır **hiç eklenmez** (mevcut prompt birebir korunur)
- Eklendikten sonra **smoke test tekrar koşulur**; tool çağrısı hâlâ yapılıyor mu ölçülür
- Bozulursa isim, sistem promptu yerine **tool sonucu mesajına** taşınır (Task 12'deki
  `CITATION_REMINDER` çözümünün aynısı)

### DoD
- [x] İsim girilince cevapta kullanılabiliyor — isim tool sonucu mesajına taşındıktan
      sonra ölçüldü (2026-08-03, `user_name='Berkin'`, iki alan içi soru):
      *"Merhaba Berkin, …"* (atıf=2, tool=1) ve *"Berkin, direktör seviyesinde … 1.500
      TL/ay"* (atıf=1, tool=1). Yalnız sistem promptundayken ikisinde de isim geçmiyordu
- [x] İsim boşken `SYSTEM_PROMPT` **birebir** eski hali — `test_without_a_user_name_the_system_prompt_is_untouched`
- [x] İsim eklendikten sonra `scripts/smoke_test.py "Berkin"` → **0 hata** (üç alan içi soruda da `tool=1`)
- [x] İsim metrik veritabanına **yazılmaz** — `test_the_user_name_never_reaches_the_database`

---

## Sıra ve bağımlılık

```
14 (kaynak) → 15 (token/kaynak sütunları) → 16 (bellek) → 17 (isim)
```

14 ve 15 bağımsız ve düşük riskli. 16 ve 17 güvenlik ağına dokunuyor; ikisi de
uçtan uca smoke test ile kapatılır.
