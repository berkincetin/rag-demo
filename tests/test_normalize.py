from src.rag.normalize import bm25_tokens, clean_text, fold_tr


def test_bm25_tokens_match_across_turkish_suffixes():
    # BM25 compares tokens exactly, so "kontrendikasyonları" in a question would
    # never match "Kontrendikasyonlar" in a section heading without truncation.
    assert bm25_tokens("kontrendikasyonları") == bm25_tokens("kontrendikasyonlar")


def test_bm25_tokens_keep_distinct_words_distinct():
    assert bm25_tokens("kontrasepsiyon") != bm25_tokens("kontrendikasyon")


def test_bm25_tokens_fold_turkish_letters():
    assert bm25_tokens("İZİN talebi") == ["izin", "talebi"]


def test_turkish_and_ascii_spellings_fold_to_the_same_string():
    assert fold_tr("İnsan Kaynakları") == fold_tr("Insan Kaynaklari") == "insan kaynaklari"


def test_dotted_capital_i_does_not_leave_a_combining_dot():
    # str.lower() turns "İ" into "i̇" (i + U+0307). That must not happen here.
    assert fold_tr("İZİN") == "izin"
    assert "̇" not in fold_tr("İZİN")


def test_dotless_i_folds_to_ascii_i():
    assert fold_tr("yıllık") == "yillik"


def test_all_turkish_specific_letters_fold():
    assert fold_tr("ŞĞÇÖÜ şğçöü") == "sgcou sgcou"


def test_runs_of_whitespace_collapse_to_one_space():
    assert fold_tr("  a\t\tb\n\nc  ") == "a b c"


def test_clean_text_preserves_paragraph_breaks_but_drops_extra_blank_lines():
    assert clean_text("a\n\n\n\nb") == "a\n\nb"


def test_clean_text_strips_trailing_spaces_on_each_line():
    assert clean_text("a   \nb  ") == "a\nb"
