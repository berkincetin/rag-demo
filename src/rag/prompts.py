"""Turkish user-facing prompt and refusal templates.

The system prompt is deliberately short. Measured on qwen2.5:7b-instruct: a
long numbered rule list suppresses tool calling entirely — the model answers
from its own knowledge instead of calling `search_documents`, even when a rule
explicitly orders it to call the tool first. A short directive prompt restores
tool calling on every probe question. The rules that were dropped from the
prompt are not lost: off-topic refusal is enforced before the LLM by the
retrieval-score gate, and "no answer without a source" is enforced after it by
the citation post-check (see agent.py).
"""

SYSTEM_PROMPT = """Sen bir şirket iç bilgi tabanı asistanısın.

Cevap vermeden önce HER ZAMAN search_documents aracını çağırmalısın.
Araç sonucunu görmeden asla cevap yazma."""

# Sent with each tool result instead of in the system prompt: instructions that
# arrive after the tool has run do not suppress the tool call.
CITATION_REMINDER = (
    "Yukarıdaki kaynaklara dayanarak Türkçe, kısa ve net cevap ver. "
    "Kullandığın her kaynağı [1], [2] gibi numaralarla göster. "
    "Kaynaklarda cevap yoksa bilgi bulunmadığını söyle, tahmin yürütme."
)

REFUSAL_TEMPLATE = (
    "Bu soru şirket bilgi tabanımın kapsamı dışında görünüyor. "
    "Ben İK politikaları, araç kullanım prosedürü, çalışan SSS, ürün taksonomisi "
    "ve ilaç kısa ürün bilgisi (KÜB) belgeleri hakkındaki soruları yanıtlayabiliyorum."
)

NO_INFO_TEMPLATE = (
    "Bu konuda bilgi tabanımda bilgi bulamadım. "
    "Soruyu farklı kelimelerle sormayı deneyebilir veya ilgili departmana danışabilirsiniz."
)
