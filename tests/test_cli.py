from src.rag.cli import format_answer
from src.rag.models import Answer


def test_format_answer_appends_a_sources_block():
    answer = Answer(text="Cevap [1].", citations=["sss.xlsx — Genel SSS, satır 4"])

    output = format_answer(answer)

    assert "Cevap [1]." in output
    assert "Kaynaklar:" in output
    assert "sss.xlsx — Genel SSS, satır 4" in output


def test_format_answer_omits_the_sources_block_when_there_are_none():
    output = format_answer(Answer(text="Bilgi bulamadım."))

    assert "Kaynaklar:" not in output


def test_format_answer_numbers_multiple_sources():
    answer = Answer(text="x", citations=["a.pdf — Bölüm 1, s.1", "b.docx — 2. BÖLÜM"])

    output = format_answer(answer)

    assert "1. a.pdf — Bölüm 1, s.1" in output
    assert "2. b.docx — 2. BÖLÜM" in output
