# Retrieval Gate Calibration — text-embedding-3-small

**Date:** 2026-08-16
**Command:** `python -m azure.scripts.calibrate`
**Index:** 276 chunks / 219 sections, embedded with `text-embedding-3-small`
**Chosen values:** `AZURE_MIN_COSINE=0.25`, `AZURE_MIN_BM25=4.22`

---

## Why this had to be measured

The local deployment gates on `MIN_COSINE=0.80` / `MIN_BM25=5.0`, calibrated in
Part 1 Task 9 against `intfloat/multilingual-e5-base`. Those values are invalid
for a different embedding model.

**How invalid: at `MIN_COSINE=0.80`, all seven valid questions would have been
refused.** The highest cosine any valid question achieves here is 0.667. The
demo would have answered nothing.

## Measured output (verbatim)

```
=== GECERLI SORULAR ===
  Yıllık izin talebimi nasıl yaparım?        0.667   21.55  calisan_sss_rehberi.xlsx — Genel SSS,
  Araç yakıt limiti ne kadar?                0.558   12.26  arac_kullanim_proseduru.docx — 3. ARAC
  OPS-PRO-003 prosedürü nedir?               0.405   14.35  arac_kullanim_proseduru.docx — Belge B
  Vitatin95 nedir?                           0.291    5.80  Anonim_Urun_Taksonomi_100Satir.xlsx —
  Şirket aracı kimlere tahsis edilir?        0.580    8.55  arac_kullanim_proseduru.docx — 1. AMAC
  İzin talebi kaç gün önce yapılmalı?        0.401    5.62  ik_surecleri_politikası.docx — 5. IZIN
  Masraf beyanı nasıl yapılır?               0.443   11.03  calisan_sss_rehberi.xlsx — Genel SSS,

=== KONU DISI SORULAR ===
  Bugün hava nasıl?                          0.359    0.00  calisan_sss_rehberi.xlsx — Onboarding
  İstanbul'un nüfusu kaç?                    0.325    0.00  Aksef 500 mg FKTB_Onaylı KUB.pdf — Böl
  Python'da liste nasıl sıralanır?           0.352    0.00  calisan_sss_rehberi.xlsx — IT Sistem R
  En iyi futbol takımı hangisi?              0.329    2.82  ik_surecleri_politikası.docx — 2. ISE
  Pizza tarifi verir misin?                  0.447    0.00  arac_kullanim_proseduru.docx — 5. YAKI

=== OZET ===
  Gecerli en dusuk kosinus : 0.291
  Konu disi en yuksek      : 0.447
  Gecerli en dusuk BM25    : 5.62
  Konu disi en yuksek BM25 : 2.82

  Kosinus tek basina ayiriyor mu? False
  BM25 tek basina ayiriyor mu?    True
  -> MIN_BM25 onerisi:   4.22
```

## The finding: the discriminating signal has swapped

Under e5-base, cosine was the tight signal and BM25 the noisy one. Under
`text-embedding-3-small` the roles have **reversed**:

| Signal | e5-base (Part 1) | text-embedding-3-small (measured here) |
|---|---|---|
| Cosine | separated cleanly | **does not separate** — ranges overlap |
| BM25 | rewarded incidental overlap | **separates cleanly**, gap of 2.80 |

Cosine ranges overlap outright: the weakest valid question ("Vitatin95 nedir?",
0.291) scores *below* the strongest off-topic one ("Pizza tarifi verir misin?",
0.447). No cosine threshold can separate these two sets.

`text-embedding-3-small` spreads similarity over a much wider band than e5,
which compressed everything into a narrow high range. A 0.29 cosine here is not
a weak match in the way 0.29 would have been under e5.

## Chosen thresholds and margin

**`AZURE_MIN_COSINE = 0.25`** — a floor, not a discriminator. It sits below the
weakest valid question (0.291, margin 0.041) and exists only to reject
pathological non-matches. It is deliberately *not* set between the two
overlapping ranges, because no such value exists.

**`AZURE_MIN_BM25 = 4.22`** — the real gate. Midpoint between the weakest valid
question (5.62) and the strongest off-topic one (2.82), giving a margin of
**1.40 on both sides**.

## Verification

Four candidate pairs were tested against the AND gate over all 12 questions:

| MIN_COSINE | MIN_BM25 | Valid passing | Off-topic passing | Verdict |
|---|---|---|---|---|
| **0.25** | **4.22** | **7/7** | **0/5** | **chosen** |
| 0.20 | 4.50 | 7/7 | 0/5 | also works |
| 0.25 | 5.00 | 7/7 | 0/5 | also works, thinner margin |
| 0.10 | 4.22 | 7/7 | 0/5 | works, weaker floor |

`0.25 / 4.22` was chosen for the widest symmetric BM25 margin while keeping a
meaningful cosine floor.

## Honest limitations

1. **BM25 now carries the gate alone in practice.** With cosine unable to
   discriminate, an off-topic question that happens to share vocabulary with the
   corpus could pass. The 12-question calibration set does not contain such a
   case; a larger adversarial set might find one.
2. **Small calibration set** — 7 valid, 5 off-topic, inherited from Part 1.
   Margins are measured against these questions, not a broad distribution.
3. **The gate is not the only defence.** The agent's citation requirement and
   the "I don't know" prompt still apply downstream of retrieval.
