"""Rolling conversation summary.

The browser keeps the last SUMMARY_BLOCK messages verbatim and folds everything
older into one cumulative summary. This module produces that summary; the
threshold and the bookkeeping live on the client, which owns conversation state.
"""

from typing import Any

_SYSTEM_PROMPT = (
    "Sen bir konuşma özetleyicisin. Sana bir konuşmanın önceki özeti ve yeni "
    "mesajları veriliyor. Bunları TEK bir bütünleşik özette birleştir. Özet, "
    "konuşmanın devamı için bağlam sağlamalı: hangi konular konuşuldu, kullanıcı "
    "neyi öğrenmek istedi, hangi bilgiler verildi. Kısa ve bilgi yoğun yaz, "
    "madde işareti kullanma, düz paragraf olsun."
)

_ROLE_LABELS = {"user": "Kullanıcı", "assistant": "Asistan"}


def build_transcript(messages: list[dict[str, str]]) -> str:
    """Render the messages as a labelled transcript, ignoring other roles."""
    return "\n".join(
        f"{_ROLE_LABELS[message['role']]}: {message.get('content', '')}"
        for message in messages
        if message.get("role") in _ROLE_LABELS
    )


def summarize_messages(llm: Any, previous_summary: str, messages: list[dict[str, str]]) -> str:
    """Fold `messages` into `previous_summary` and return the merged summary."""
    if not messages:
        raise ValueError("Özetlenecek mesaj yok.")

    user_prompt = (
        f"ÖNCEKİ ÖZET:\n{previous_summary or '(Henüz özet yok)'}\n\n"
        f"YENİ MESAJLAR:\n{build_transcript(messages)}\n\n"
        "Yukarıdakileri tek bir güncel özette birleştir."
    )
    # No tools: summarising must not trigger a document search.
    response = llm.chat(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    return response.text or ""
