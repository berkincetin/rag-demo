# Task 8: Otomatik değerlendirme

> [00-overview.md](00-overview.md) — global kısıtlar. Tasarım: spec §4.8.
> **Önceki:** [Task 7](07-ollama-yonetici.md) · **Sonraki:** [Task 9](09-ui-saglayicilar.md)

**Dosyalar:** `src/rag/evaluation.py`, `config/eval_set.json`
**Test:** `tests/test_evaluation.py`

**Üretir:** `EvalCase`, `EvalResult`, `load_eval_set()`, `evaluate(agent, cases)`

🚨 **LLM-as-judge kullanılmaz.** Puanlama deterministik: atıf var mı, doğru dosyaya mı,
kapı doğru mu karar verdi, beklenen kanıt metni geçiyor mu. Cevabın **üslubu** ölçülmez.

## Soru seti — `config/eval_set.json`

PRD §7'deki 8 demo sorusu + 5 konu dışı. Her geçerli soru beklenen kaynağı ve (varsa)
kanıt metnini taşır:

```json
[
  {"question": "Yıllık izin talebimi nasıl yaparım?",
   "expect_answer": true, "expect_source": "calisan_sss_rehberi.xlsx", "expect_evidence": null},
  {"question": "Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?",
   "expect_answer": true, "expect_source": "arac_kullanim_proseduru.docx",
   "expect_evidence": "1.500 TL/ay"},
  {"question": "Aksef 500 mg'ın kontrendikasyonları nelerdir?",
   "expect_answer": true, "expect_source": "Aksef", "expect_evidence": null},
  {"question": "Bugün hava nasıl olacak?", "expect_answer": false},
  {"question": "Şirketin 2027 yılı kâr hedefi nedir?", "expect_answer": false}
]
```

> `expect_source` **alt dize** olarak eşleşir (dosya adları uzun ve Türkçe karakterli).
> Aksef sorusunda `expect_evidence` `null` — Task 14'te ölçüldüğü gibi model doğru dosyayı
> ama bazen yanlış **bölümü** işaretliyor; bölüm isabetini burada zorlamak yanlış negatif üretir.

- [ ] **Adım 1: Kırmızı test**

```python
# tests/test_evaluation.py
from src.rag.evaluation import EvalCase, evaluate, load_eval_set
from src.rag.models import Answer


class _FakeAgent:
    def __init__(self, answers):
        self._answers = answers

    def answer(self, question):
        return self._answers[question]


def test_a_cited_correct_answer_scores_full_marks():
    cases = [EvalCase("Yakıt limiti?", True, "arac_kullanim", "1.500 TL/ay")]
    agent = _FakeAgent({
        "Yakıt limiti?": Answer(
            text="Limit 1.500 TL/ay'dır [1].",
            citations=["arac_kullanim_proseduru.docx — 3. ARAC TAHSIS"],
        )
    })

    result = evaluate(agent, cases)

    assert result.citation_rate == 1.0
    assert result.source_accuracy == 1.0
    assert result.evidence_hit == 1.0


def test_an_uncited_answer_lowers_the_citation_rate():
    cases = [EvalCase("Soru?", True, "dosya", None)]
    agent = _FakeAgent({"Soru?": Answer(text="Bilgi bulamadım.", citations=[])})

    assert evaluate(agent, cases).citation_rate == 0.0


def test_citing_the_wrong_document_lowers_source_accuracy():
    cases = [EvalCase("Soru?", True, "arac_kullanim", None)]
    agent = _FakeAgent({"Soru?": Answer(text="Cevap [1].", citations=["Duxet ... KUB.pdf"])})

    result = evaluate(agent, cases)

    assert result.citation_rate == 1.0
    assert result.source_accuracy == 0.0


def test_refusing_an_off_topic_question_counts_as_correct():
    cases = [EvalCase("Hava nasıl?", False, None, None)]
    agent = _FakeAgent({"Hava nasıl?": Answer(text="Kapsam dışında.", citations=[])})

    assert evaluate(agent, cases).refusal_accuracy == 1.0


def test_answering_an_off_topic_question_is_a_failure():
    cases = [EvalCase("Hava nasıl?", False, None, None)]
    agent = _FakeAgent({"Hava nasıl?": Answer(text="Yağmurlu [1].", citations=["a.pdf"])})

    assert evaluate(agent, cases).refusal_accuracy == 0.0


def test_rates_are_computed_only_over_applicable_cases():
    # citation_rate yalnız geçerli sorulardan; refusal_accuracy yalnız konu dışı olanlardan.
    cases = [EvalCase("Geçerli?", True, "a", None), EvalCase("Konu dışı?", False, None, None)]
    agent = _FakeAgent({
        "Geçerli?": Answer(text="Cevap [1].", citations=["a.pdf"]),
        "Konu dışı?": Answer(text="Kapsam dışında.", citations=[]),
    })

    result = evaluate(agent, cases)

    assert result.citation_rate == 1.0
    assert result.refusal_accuracy == 1.0
    assert result.cases == 2


def test_the_shipped_eval_set_loads_and_covers_both_kinds():
    cases = load_eval_set()

    assert any(c.expect_answer for c in cases)
    assert any(not c.expect_answer for c in cases)
```

- [ ] **Adım 2: Kırmızıyı doğrula**

- [ ] **Adım 3: `evaluation.py` + `config/eval_set.json` yaz**

`EvalResult` alanları: `model_id`, `cases`, `citation_rate`, `source_accuracy`,
`evidence_hit`, `refusal_accuracy`, `avg_latency_ms`, `total_cost_usd`, `unpriced_runs`.

Oranlar **yalnız uygulanabilir vakalardan** hesaplanır; payda 0 ise `None` döner
(0.0 "başarısız" demek olurdu, "ölçülmedi" değil).

`evaluate()` her vakayı `agent.answer()` ile çalıştırır; `Answer.latency_ms` ve
`Answer.usage`'dan gecikme/maliyet toplar (Task 6). Maliyeti bilinmeyen koşular
`unpriced_runs` olarak ayrıca sayılır.

- [ ] **Adım 4: Yeşili doğrula** — 7 test geçmeli

- [ ] **Adım 5: Gerçek modelle bir kez çalıştır** ⚠️ Yavaş (~13 soru × 40–460 sn)

```bash
python -c "from src.rag.cli import build_agent; from src.rag.evaluation import *; print(evaluate(build_agent(), load_eval_set()))"
```
Sonuç MEMORY.md'ye taban çizgisi olarak yazılır — sonraki modeller bununla karşılaştırılır.

- [ ] **Adım 6: Kalite kapısı ve commit**

```bash
git commit -m "feat(eval): add deterministic quality evaluation over a fixed question set"
```

## Definition of Done
- [ ] 7 test yeşil, `evaluation.py` ≥ %95 kapsanmış
- [ ] Oranlar yalnız uygulanabilir vakalardan; boş payda `None`
- [ ] Gerçek modelle bir taban çizgisi ölçüldü ve MEMORY.md'ye yazıldı
- [ ] Hiçbir yerde LLM-as-judge yok
