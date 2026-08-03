import inspect

from src.rag.memory import ConversationMemory, retrieval_query


def test_turns_are_remembered_in_order():
    memory = ConversationMemory()
    memory.add("İlk soru", "İlk cevap")
    memory.add("İkinci soru", "İkinci cevap")

    assert [turn.question for turn in memory.recent_turns()] == ["İlk soru", "İkinci soru"]


def test_only_the_last_n_turns_are_kept():
    # Long context is slow on a 7B model, so the window is deliberately small.
    memory = ConversationMemory(max_turns=2)
    for index in range(4):
        memory.add(f"soru {index}", f"cevap {index}")

    assert [turn.question for turn in memory.recent_turns()] == ["soru 2", "soru 3"]


def test_clear_empties_the_history():
    memory = ConversationMemory()
    memory.add("soru", "cevap")

    memory.clear()

    assert memory.recent_turns() == []


def test_history_becomes_chat_messages():
    memory = ConversationMemory()
    memory.add("Yıllık izin nasıl alınır?", "HRPortal üzerinden.")

    messages = memory.as_messages()

    assert messages == [
        {"role": "user", "content": "Yıllık izin nasıl alınır?"},
        {"role": "assistant", "content": "HRPortal üzerinden."},
    ]


def test_a_follow_up_question_is_enriched_for_retrieval():
    # "peki ya müdür?" matches no document on its own — the score gate would
    # refuse it. Enriching the retrieval query with the previous question keeps
    # the gate accurate without changing what the user typed.
    memory = ConversationMemory()
    memory.add("Direktör seviyesindeki yakıt limiti nedir?", "1.500 TL/ay")

    query = retrieval_query("peki ya müdür seviyesinde?", memory)

    assert "yakıt limiti" in query
    assert "müdür seviyesinde" in query


def test_the_first_question_is_used_as_is():
    assert retrieval_query("Yıllık izin?", ConversationMemory()) == "Yıllık izin?"


def test_only_the_last_turn_enriches_the_query():
    # Pulling the whole history in would drown the actual question.
    memory = ConversationMemory()
    memory.add("Çok eski konu", "cevap")
    memory.add("Yakıt limiti nedir?", "1.500 TL/ay")

    query = retrieval_query("peki ya müdür?", memory)

    assert "Çok eski konu" not in query


def test_memory_module_never_writes_to_disk():
    # Same reasoning as API keys: conversation content stays in the session.
    source = inspect.getsource(inspect.getmodule(ConversationMemory))

    for forbidden in ("open(", "Path(", "json.dump", "write_text", "sqlite3"):
        assert forbidden not in source
