from src.rag.evaluation import EvalCase, evaluate, load_eval_set
from src.rag.models import Answer


class _FakeAgent:
    def __init__(self, answers, model="test-model"):
        self._answers = answers
        self.llm = type("LLM", (), {"model": model})()

    def answer(self, question):
        return self._answers[question]


def test_a_cited_correct_answer_scores_full_marks():
    cases = [EvalCase("Yakıt limiti?", True, "arac_kullanim", "1.500 TL/ay")]
    agent = _FakeAgent(
        {
            "Yakıt limiti?": Answer(
                text="Limit 1.500 TL/ay'dır [1].",
                citations=["arac_kullanim_proseduru.docx — 3. ARAC TAHSIS"],
            )
        }
    )

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
    agent = _FakeAgent({"Soru?": Answer(text="Cevap [1].", citations=["Duxet 30 mg KUB.pdf"])})

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
    cases = [EvalCase("Geçerli?", True, "a", None), EvalCase("Konu dışı?", False, None, None)]
    agent = _FakeAgent(
        {
            "Geçerli?": Answer(text="Cevap [1].", citations=["a.pdf"]),
            "Konu dışı?": Answer(text="Kapsam dışında.", citations=[]),
        }
    )

    result = evaluate(agent, cases)

    assert result.citation_rate == 1.0
    assert result.refusal_accuracy == 1.0
    assert result.cases == 2


def test_a_rate_with_no_applicable_cases_is_none_not_zero():
    # Zero would read as "failed everything"; None reads as "nothing to measure".
    cases = [EvalCase("Konu dışı?", False, None, None)]
    agent = _FakeAgent({"Konu dışı?": Answer(text="Kapsam dışında.", citations=[])})

    assert evaluate(agent, cases).citation_rate is None


def test_evidence_is_only_scored_when_a_case_declares_it():
    cases = [EvalCase("Soru?", True, "a", None)]
    agent = _FakeAgent({"Soru?": Answer(text="Cevap [1].", citations=["a.pdf"])})

    assert evaluate(agent, cases).evidence_hit is None


def test_the_shipped_eval_set_loads_and_covers_both_kinds():
    cases = load_eval_set()

    assert any(case.expect_answer for case in cases)
    assert any(not case.expect_answer for case in cases)
    assert any(case.expect_evidence for case in cases)
