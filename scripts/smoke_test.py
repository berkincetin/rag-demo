"""End-to-end smoke test: runs a fixed question set against a live agent.

Used to verify a deployment (Docker or local) actually answers, cites, and
refuses. Prints one line per check so the output is diffable across runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.cli import build_agent  # noqa: E402

# (question, must the gate pass?, expected substring in the answer or "")
CASES = [
    ("Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?", True, "1.500"),
    ("Vitatin95 ürününün ürün müdürü kim?", True, ""),
    ("Yıllık izin talebimi nasıl yaparım?", True, ""),
    ("Bugün hava nasıl olacak?", False, ""),
    ("Şirketin 2027 yılı kâr hedefi nedir?", False, ""),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    # A user name appends a sentence to the system prompt, and Task 12 measured
    # that every extra sentence there can suppress the tool call. Passing one
    # here is how that risk is re-measured after the personalisation change.
    user_name = sys.argv[1] if len(sys.argv) > 1 else None
    agent = build_agent()
    failures = 0

    if user_name:
        print(f"Kullanıcı adı: {user_name}\n")

    for question, should_pass, needle in CASES:
        hits = agent.retriever.search(question, top_k=5)
        confident = agent.retriever.is_confident(hits)
        answer = agent.answer(question, user_name=user_name)

        checks = [("kapı", confident == should_pass)]
        if should_pass:
            checks.append(("atıf", bool(answer.citations)))
            checks.append(("tool", bool(answer.tool_trace)))
            if needle:
                checks.append(("içerik", needle in answer.text))
        else:
            checks.append(("tool yok", not answer.tool_trace))

        bad = [name for name, ok in checks if not ok]
        failures += len(bad)
        durum = "GEÇTİ " if not bad else f"HATA({','.join(bad)})"
        print(f"[{durum}] {question}")
        print(f"          kosinüs={hits[0].cosine:.3f} bm25={hits[0].bm25:.2f} kapı={confident}")
        print(f"          atıf={len(answer.citations)} tool={len(answer.tool_trace)}")
        print(f"          cevap: {answer.text[:110].replace(chr(10), ' ')}")

    print(f"\nBaşarısız kontrol sayısı: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
