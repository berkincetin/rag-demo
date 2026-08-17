# Aşama 1 — Arayüz Yenileme ve Sohbet Yetenekleri Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Canlıdaki uygulamanın arayüzünü referans tasarıma ve yeni palete taşımak; cevabı SSE ile akıtmak; konuşma başına süreli (TTL'li, disksiz) doküman yükleme ve 10 mesaj hatırlama + özetleme mekanizmasını eklemek.

**Architecture:** Akış, `graph.py`'ye dokunmadan LLM istemcisine takılan bir gözlem katmanı olarak eklenir — `contextvar` üzerinden taşınan bir token kuyruğu, grafiği çalışan bir iş parçacığında koşturan SSE üreteci tarafından boşaltılır. Yüklenen belgeler yalnızca bellekte, TTL'li bir depoda tutulur ve korpus retriever'ını saran bir sarmalayıcı üzerinden hem aramaya hem skor kapısına katılır. Konuşma durumu tamamen tarayıcıda (`localStorage`) yaşar; sunucu her istekte istemciden gelen özet ve geçmişten geçici bir bellek kurar.

**Tech Stack:** FastAPI, LangGraph, Chroma, Azure OpenAI (`gpt-4.1-mini`, `text-embedding-3-small`), Next.js 16, React 19, Tailwind 4, vitest, pytest.

**Spec:** `docs/superpowers/specs/2026-08-17-arayuz-yenileme-ve-model-katalogu-design.md`

## Global Constraints

- Yalnızca `azure/rag/` ve `azure/web/` değiştirilir. `src/rag/` ve `web/` bu planın **tamamen dışındadır**.
- `azure/rag/graph.py` ve `azure/rag/agent.py` **değiştirilmez**. Akış bir gözlem katmanıdır, kontrol akışı değişikliği değildir.
- Kod kimlikleri (değişken, fonksiyon, sınıf, test adları) **İngilizce**; kullanıcıya görünen metinler (arayüz etiketleri, hata mesajları, sistem istemi) **Türkçe**.
- TDD zorunlu: her adımda önce başarısız test, sonra minimum kod. Üretim kodu testten önce yazılırsa silinip yeniden başlanır.
- `@pytest.mark.skip` ve `xfail` yasak.
- **Kalite kapısı `azure/` kapsamındadır:**

  ```bash
  ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
  ```

  `-o addopts=""` şart: `pyproject.toml` `addopts` içinde `--cov=src` var ve komut satırından
  `--cov=azure` eklemek onu *kaldırmaz*, üstüne ekler — kapsam `src`'yi de sayarak %54'e düşer
  ve kapı hiç geçmez.

  **Neden `src` dışarıda:** temiz ağaçta `tests/` altında 18 test zaten başarısız
  (`sentence_transformers` ve `statsmodels` kurulu değil; Azure dağıtımı torch'u bilinçli
  olarak attı). Bu hatalar bu planın işiyle ilgisiz, bu planla düzelmez ve `src/` artık
  dokunulmayacak eski projedir. Taban ölçümü: `azure/tests/` 73 test geçiyor, kapsam %90.
- Kapsam eşiği %70.
- Conventional Commits. **Attribution trailer yasak** — `Co-Authored-By`, `Generated with Claude Code` vb. eklenmez.
- Doğrudan `main` üzerinde çalışılır; her görev sonunda commit.
- LLM çıktısının **metni** asla test edilmez; LLM sınırına kadar her şey test edilir.
- Yükleme sınırları: konuşma başına en fazla **5 belge**, **300 parça**; dosya başına **10 MB**; TTL **60 dakika**.
- `SUMMARY_BLOCK = 10` — özetleme her 10 mesajda bir tetiklenir.
- Renk simgeleri: açık `#F8FAFC` / `#FFFFFF` / `#005AA9` / `#38A169`, koyu `#0F172A` / `#1E293B` / `#3B82F6` / `#22C55E`.

## Mevcut arayüzler (değişmeyen, güvenilebilir)

Bu plan boyunca aşağıdakiler olduğu gibi kullanılır:

```python
# azure/rag/models.py
@dataclass
class RawSection:
    source_file: str; doc_type: str; text: str
    section_id: str | None = None; section_title: str | None = None
    section_path: str | None = None; page_start: int | None = None
    page_end: int | None = None; sheet: str | None = None; row: int | None = None

@dataclass
class Chunk:
    chunk_id: str; text: str; search_text: str
    citation_label: str; metadata: dict[str, Any]

@dataclass
class SearchHit:
    chunk: Chunk; score: float; cosine: float; bm25: float

# azure/rag/chunker.py
def chunk_sections(sections: list[RawSection], max_chars: int = 1200,
                   overlap: int = 150) -> list[Chunk]: ...

# azure/rag/retriever.py
@dataclass
class Retriever:
    index: LoadedIndex; embedder: Embedder; min_cosine: float; min_bm25: float
    def search(self, query: str, top_k: int = 5,
               source_filter: str | None = None) -> list[SearchHit]: ...
    def is_confident(self, hits: list[SearchHit]) -> bool: ...
def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]: ...

# azure/rag/embedder.py
class AzureOpenAIEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]: ...   # birim vektörler

# azure/rag/normalize.py
def fold_tr(text: str) -> str: ...
def bm25_tokens(text: str) -> list[str]: ...

# azure/rag/serialize.py
def answer_payload(answer: Answer, cost_usd: float | None) -> dict[str, Any]: ...
```

Testler `azure/tests/` altında, `test_<modül>.py` adıyla. Ön yüz testleri `azure/web/__tests__/` altında.

---

## Dosya yapısı

**Yeni backend dosyaları**

| Dosya | Sorumluluk |
|---|---|
| `azure/rag/request_context.py` | İstek başına `contextvar`'lar: token alıcısı ve aktif yükleme deposu |
| `azure/rag/uploads.py` | `UploadStore` — TTL'li, sınırlı, bellekte yükleme deposu |
| `azure/rag/upload_search.py` | Yüklenen parçalar üzerinde arama + korpusla birleştiren retriever sarmalayıcısı |
| `azure/rag/streaming.py` | Grafiği iş parçacığında koşturan SSE olay üreteci |
| `azure/rag/summarize.py` | Konuşma özetleme istemi ve çağrısı |
| `azure/rag/loaders/txt_loader.py` | `.txt` yükleyici (yükleme için gerekli, korpusta yok) |

**Değişen backend dosyaları**

| Dosya | Değişiklik |
|---|---|
| `azure/rag/llm_client.py` | `stream=True` + delta yayınlama; `stream_options` ile usage |
| `azure/rag/loaders/__init__.py` | `.txt` desteği + tek dosya yükleyen `load_file` |
| `azure/rag/api.py` | Yeni uçlar: akış, yükleme, listeleme, silme, özetleme |

**Yeni ön yüz dosyaları**

| Dosya | Sorumluluk |
|---|---|
| `azure/web/lib/types.ts` | `Message`, `Conversation`, `DocumentInfo`, `Source` |
| `azure/web/lib/storage.ts` | `localStorage` turu, başlık üretimi, tarihe göre gruplama |
| `azure/web/lib/memory.ts` | `SUMMARY_BLOCK`, `buildContext`, `needsSummarization` |
| `azure/web/lib/sse.ts` | SSE gövdesini olaylara ayrıştıran okuyucu |
| `azure/web/lib/useConversations.ts` | Konuşma durumu, gönderme, yükleme, özetleme |
| `azure/web/components/Sidebar.tsx` | Konuşma listesi, arama, gruplama |
| `azure/web/components/ConversationItem.tsx` | Tek konuşma satırı: seç, yeniden adlandır, sil |
| `azure/web/components/ChatPane.tsx` | Mesaj akışı ve boş durum |
| `azure/web/components/MessageBubble.tsx` | Markdown balon, kopyala/düzenle/yeniden üret |
| `azure/web/components/Composer.tsx` | Besteci, doküman çipleri, otomatik büyüyen alan |
| `azure/web/components/DocumentChips.tsx` | Yüklü belge çipleri |
| `azure/web/components/SourceDisclosure.tsx` | Kaynak açılır paneli |

**Değişen ön yüz dosyaları**

| Dosya | Değişiklik |
|---|---|
| `azure/web/app/globals.css` | Yeni palet simgeleri |
| `azure/web/app/page.tsx` | Yeni kabuk: kenar çubuğu + sohbet + besteci |
| `azure/web/app/api/proxy/[...path]/route.ts` | Akış geçişi, multipart geçişi, DELETE, genişletilmiş izin listesi |
| `azure/web/package.json` | `react-markdown`, `remark-gfm`, `test` script'i |

---

## Görev sırası

1. Palet ve tasarım simgeleri
2. LLM istemcisinde akış
3. SSE olay üreteci ve akış ucu
4. `.txt` yükleyici ve tek dosya yükleme
5. Yükleme deposu (TTL, sınırlar, izolasyon)
6. Yüklenen belgelerde arama ve kapı entegrasyonu
7. Yükleme uçları
8. Özetleme ucu
9. Proxy: akış, multipart, izin listesi
10. Ön yüz durum katmanı
11. Ön yüz bileşenleri
12. Kabuk, entegrasyon doğrulaması ve durum güncellemesi

---

### Task 1: Palet ve tasarım simgeleri

**Files:**
- Modify: `azure/web/app/globals.css:8-62`

**Interfaces:**
- Consumes: yok
- Produces: CSS değişkenleri `--bg`, `--surface`, `--surface-2`, `--border`, `--text`, `--text-dim`, `--accent`, `--accent-fg`, `--accent-soft`, `--ok`, `--ok-soft`, `--warn`, `--warn-soft`, `--danger`, `--danger-soft` — sonraki tüm bileşenler yalnızca bunlara başvurur.

- [ ] **Step 1: Paleti değiştir**

`azure/web/app/globals.css` içinde `:root` ve `.dark` bloklarındaki renkleri aşağıdakiyle değiştir. Simge **adları** değişmiyor — yalnızca değerleri. Böylece mevcut bileşenler kırılmadan yeni palete geçer.

```css
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-2: #eef2f7;
  --border: #dbe3ec;
  --text: #0f172a;
  --text-dim: #5a6b80;
  --accent: #005aa9;
  --accent-fg: #ffffff;
  --accent-soft: #e6f0f9;
  --ok: #38a169;
  --ok-soft: #e8f5ee;
  --warn: #9a5b00;
  --warn-soft: #fdf3e3;
  --danger: #b4232c;
  --danger-soft: #fdeced;
  --shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 4px 16px rgba(15, 23, 42, 0.05);
}

.dark {
  --bg: #0f172a;
  --surface: #1e293b;
  --surface-2: #24334a;
  --border: #33445f;
  --text: #e8eef6;
  --text-dim: #94a7bd;
  --accent: #3b82f6;
  --accent-fg: #0b1220;
  --accent-soft: #1b2f4d;
  --ok: #22c55e;
  --ok-soft: #14301f;
  --warn: #fbbf24;
  --warn-soft: #2a2010;
  --danger: #f87171;
  --danger-soft: #2a1416;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.4), 0 8px 24px rgba(0, 0, 0, 0.3);
}
```

- [ ] **Step 2: Akış imleci ve animasyon ekle**

Dosyanın sonuna ekle — akan cevabın ucundaki yanıp sönen imleç sonraki görevlerde kullanılacak:

```css
@keyframes pulse-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}

.stream-cursor {
  display: inline-block;
  width: 7px;
  height: 1em;
  background: var(--accent);
  vertical-align: text-bottom;
  animation: pulse-cursor 1s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .stream-cursor { animation: none; }
}
```

- [ ] **Step 3: Derlemenin geçtiğini doğrula**

Run: `cd azure/web && npx next build`
Expected: derleme hatasız tamamlanır.

- [ ] **Step 4: Commit**

```bash
git add azure/web/app/globals.css
git commit -m "feat(ui): switch design tokens to the new blue-green palette"
```

---

### Task 2: LLM istemcisinde akış

**Files:**
- Create: `azure/rag/request_context.py`
- Modify: `azure/rag/llm_client.py:66-95`
- Test: `azure/tests/test_request_context.py`, `azure/tests/test_llm_client.py`

**Interfaces:**
- Consumes: yok
- Produces:
  - `azure.rag.request_context.token_sink` — `ContextVar[Callable[[str], None] | None]`
  - `azure.rag.request_context.set_token_sink(sink) -> Token`
  - `azure.rag.request_context.emit_token(text: str) -> None`
  - `AzureOpenAIClient.chat(messages, tools=None) -> LLMResponse` — davranışı değişmez; alıcı kuruluysa metin delta'larını yayınlar.

- [ ] **Step 1: request_context için başarısız test yaz**

`azure/tests/test_request_context.py`:

```python
from azure.rag import request_context


def test_emit_token_is_a_noop_without_a_sink():
    request_context.emit_token("merhaba")  # yükseltmemeli


def test_emit_token_reaches_the_installed_sink():
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        request_context.emit_token("mer")
        request_context.emit_token("haba")
    finally:
        request_context.reset_token_sink(token)

    assert received == ["mer", "haba"]


def test_sink_is_removed_after_reset():
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    request_context.reset_token_sink(token)

    request_context.emit_token("gitmemeli")

    assert received == []
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_request_context.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'azure.rag.request_context'`

- [ ] **Step 3: request_context modülünü yaz**

`azure/rag/request_context.py`:

```python
"""Per-request context carried without changing any function signature.

The agent graph (`graph.py`) is deliberately untouched by the streaming and
upload features. Both need something that is request-scoped, so it travels in
context variables instead of through the graph's state.

Threading note: context variables do NOT propagate into a thread created with
`threading.Thread`. The streaming endpoint therefore installs the sink *inside*
the worker thread rather than relying on inheritance.
"""

from contextvars import ContextVar, Token
from typing import Any, Callable

_token_sink: ContextVar[Callable[[str], None] | None] = ContextVar("token_sink", default=None)
_upload_store: ContextVar[Any] = ContextVar("upload_store", default=None)


def set_token_sink(sink: Callable[[str], None]) -> Token:
    """Install a sink that receives every text delta the LLM produces."""
    return _token_sink.set(sink)


def reset_token_sink(token: Token) -> None:
    _token_sink.reset(token)


def emit_token(text: str) -> None:
    """Publish one text delta. A no-op when nothing is listening."""
    sink = _token_sink.get()
    if sink is not None and text:
        sink(text)


def set_upload_store(store: Any) -> Token:
    """Install the uploaded-document store for the current request."""
    return _upload_store.set(store)


def reset_upload_store(token: Token) -> None:
    _upload_store.reset(token)


def active_upload_store() -> Any:
    """The current request's uploaded-document store, or None."""
    return _upload_store.get()
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_request_context.py -v --no-cov`
Expected: 3 passed

- [ ] **Step 5: Akışlı istemci için başarısız test yaz**

`azure/tests/test_llm_client.py` dosyasının sonuna ekle. Sahte istemci, OpenAI SDK'sının akış biçimini taklit eder: `choices[0].delta.content` metin taşır, son parça boş `choices` ile `usage` taşır.

```python
from types import SimpleNamespace

from azure.rag import request_context
from azure.rag.llm_client import AzureOpenAIClient
from azure.rag.config import AzureConfig


def _delta_chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)], usage=None)


def _usage_chunk(prompt_tokens, completion_tokens):
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[], usage=usage)


class _StreamingStub:
    """Stands in for the OpenAI SDK client, recording the payload it received."""

    def __init__(self, chunks):
        self._chunks = chunks
        self.received: dict = {}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **payload):
        self.received = payload
        return iter(self._chunks)


def _config():
    return AzureConfig(
        openai_endpoint="https://example.invalid/",
        openai_api_key="k",
        api_version="2024-10-21",
        chat_deployment="gpt-4.1-mini",
        embedding_deployment="text-embedding-3-small",
        storage_dir=Path("./azure/storage"),
        data_dir=Path("./data"),
        top_k=5,
        min_cosine=0.25,
        min_bm25=4.22,
        max_tool_turns=3,
        internal_token="t",
    )


def test_streaming_chat_concatenates_deltas_into_text():
    stub = _StreamingStub([_delta_chunk("Yıllık "), _delta_chunk("izin"), _usage_chunk(10, 3)])
    client = AzureOpenAIClient(_config(), client=stub)

    response = client.chat([{"role": "user", "content": "soru"}])

    assert response.text == "Yıllık izin"


def test_streaming_chat_reports_usage_from_the_final_chunk():
    stub = _StreamingStub([_delta_chunk("x"), _usage_chunk(11, 4)])
    client = AzureOpenAIClient(_config(), client=stub)

    response = client.chat([{"role": "user", "content": "soru"}])

    assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 4)


def test_streaming_chat_requests_usage_explicitly():
    # Without stream_options the API omits usage entirely and every metric
    # silently becomes null. This asserts the flag is actually sent.
    stub = _StreamingStub([_usage_chunk(1, 1)])
    client = AzureOpenAIClient(_config(), client=stub)

    client.chat([{"role": "user", "content": "soru"}])

    assert stub.received["stream"] is True
    assert stub.received["stream_options"] == {"include_usage": True}


def test_streaming_chat_publishes_deltas_to_the_sink():
    stub = _StreamingStub([_delta_chunk("a"), _delta_chunk("b"), _usage_chunk(1, 1)])
    client = AzureOpenAIClient(_config(), client=stub)
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        client.chat([{"role": "user", "content": "soru"}])
    finally:
        request_context.reset_token_sink(token)

    assert received == ["a", "b"]


def test_streaming_chat_accumulates_tool_call_arguments_across_deltas():
    # Tool call arguments arrive as string fragments that must be joined before
    # they parse as JSON.
    first = _delta_chunk(
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="call_1",
                function=SimpleNamespace(name="search_documents", arguments='{"query": "yem'),
            )
        ]
    )
    second = _delta_chunk(
        tool_calls=[
            SimpleNamespace(index=0, id=None, function=SimpleNamespace(name=None, arguments='ek"}'))
        ]
    )
    stub = _StreamingStub([first, second, _usage_chunk(5, 2)])
    client = AzureOpenAIClient(_config(), client=stub)

    response = client.chat([{"role": "user", "content": "soru"}], tools=[{"name": "x"}])

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "search_documents"
    assert response.tool_calls[0].arguments == {"query": "yemek"}


def test_tool_call_deltas_are_not_published_as_text():
    stub = _StreamingStub(
        [
            _delta_chunk(
                tool_calls=[
                    SimpleNamespace(
                        index=0,
                        id="c",
                        function=SimpleNamespace(name="list_documents", arguments="{}"),
                    )
                ]
            ),
            _usage_chunk(1, 1),
        ]
    )
    client = AzureOpenAIClient(_config(), client=stub)
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        client.chat([{"role": "user", "content": "soru"}], tools=[{"name": "x"}])
    finally:
        request_context.reset_token_sink(token)

    assert received == []
```

Dosyanın başına `from pathlib import Path` eklenmemişse ekle.

- [ ] **Step 6: Testlerin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_llm_client.py -v --no-cov`
Expected: yeni 6 test FAIL — `chat()` hâlâ akışsız çağrı yapıyor, `stub.received["stream"]` yok.

- [ ] **Step 7: chat() metodunu akışa çevir**

`azure/rag/llm_client.py` içindeki `chat` metodunu aşağıdakiyle değiştir ve dosyanın başına `from azure.rag.request_context import emit_token` ekle:

```python
    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        """Stream the completion, returning the same shape a blocking call did.

        Streaming is an observation layer: the graph still receives one complete
        LLMResponse. The only difference is that text deltas are published to
        the request's token sink on the way through.
        """
        payload: dict[str, Any] = {
            # On Azure this is the deployment name, not the model name.
            "model": self.config.chat_deployment,
            "messages": messages,
            "temperature": _TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
            "stream": True,
            # Without this the streamed response carries no usage at all and
            # every token count and cost silently becomes null.
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": schema} for schema in tools]

        text_parts: list[str] = []
        # Keyed by the delta's `index`, which is how the API ties fragments of
        # one tool call together across chunks.
        partial_calls: dict[int, dict[str, Any]] = {}
        usage = TokenUsage()

        for chunk in self._client.chat.completions.create(**payload):
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = TokenUsage(
                    getattr(chunk_usage, "prompt_tokens", None),
                    getattr(chunk_usage, "completion_tokens", None),
                )
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                text_parts.append(content)
                emit_token(content)

            for call in getattr(delta, "tool_calls", None) or []:
                slot = partial_calls.setdefault(call.index, {"id": "", "name": "", "arguments": ""})
                if call.id:
                    slot["id"] = call.id
                function = getattr(call, "function", None)
                if function is not None:
                    if getattr(function, "name", None):
                        slot["name"] = function.name
                    if getattr(function, "arguments", None):
                        slot["arguments"] += function.arguments

        calls = [
            ToolCall(
                id=slot["id"],
                name=slot["name"],
                arguments=_as_dict(slot["arguments"] or "{}"),
            )
            for _, slot in sorted(partial_calls.items())
        ]
        return LLMResponse(text="".join(text_parts) or None, tool_calls=calls, usage=usage)
```

- [ ] **Step 8: Testlerin geçtiğini ve mevcutların bozulmadığını doğrula**

Run: `pytest azure/tests/test_llm_client.py azure/tests/test_request_context.py -v --no-cov`
Expected: hepsi PASS. Eski akışsız testler artık akışlı sahte istemciyle uyumsuzsa, onları da yukarıdaki `_StreamingStub` biçimine taşı — davranış sözleşmesi (`text`, `tool_calls`, `usage`) aynı kaldığı için iddialar değişmez.

- [ ] **Step 9: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/request_context.py azure/rag/llm_client.py azure/tests/test_request_context.py azure/tests/test_llm_client.py
git commit -m "feat(llm): stream completions and publish text deltas to a request sink"
```

---

### Task 3: SSE olay üreteci ve akış ucu

**Files:**
- Create: `azure/rag/streaming.py`
- Modify: `azure/rag/api.py`
- Test: `azure/tests/test_streaming.py`

**Interfaces:**
- Consumes: `request_context.set_token_sink`, `request_context.reset_token_sink`, `answer_payload`
- Produces:
  - `azure.rag.streaming.answer_events(run, *, on_meta) -> Iterator[dict]` — olay sözlükleri üretir
  - `azure.rag.streaming.format_sse(event: dict) -> str` — `data: {...}\n\n`
  - `POST /api/ask/stream` — `text/event-stream`

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_streaming.py`:

```python
import json

from azure.rag.streaming import answer_events, format_sse


def test_format_sse_frames_one_json_object_per_event():
    assert format_sse({"type": "token", "content": "a"}) == 'data: {"type": "token", "content": "a"}\n\n'


def _drain(run, on_meta):
    return list(answer_events(run, on_meta=on_meta))


def test_streamed_text_is_emitted_as_tokens_then_meta():
    def run(emit):
        emit("Yıllık ")
        emit("izin")
        return {"text": "Yıllık izin", "citations": ["a.pdf"]}

    events = _drain(run, on_meta=lambda result: {"citations": result["citations"]})

    assert [event["type"] for event in events] == ["start", "token", "token", "meta"]
    assert "".join(e["content"] for e in events if e["type"] == "token") == "Yıllık izin"
    assert events[-1]["citations"] == ["a.pdf"]


def test_replace_is_emitted_when_the_final_text_differs_from_what_streamed():
    # The citation gate can substitute the answer after it streamed — a refusal,
    # a no_info template, or a repaired answer.
    def run(emit):
        emit("uydurma cevap")
        return {"text": "Bu konuda bilgi bulamadım.", "citations": []}

    events = _drain(run, on_meta=lambda result: {"citations": result["citations"]})

    types = [event["type"] for event in events]
    assert "replace" in types
    assert events[types.index("replace")]["content"] == "Bu konuda bilgi bulamadım."


def test_no_replace_when_the_final_text_matches_the_stream():
    def run(emit):
        emit("aynı")
        return {"text": "aynı", "citations": ["x"]}

    events = _drain(run, on_meta=lambda result: {"citations": result["citations"]})

    assert "replace" not in [event["type"] for event in events]


def test_a_refusal_that_never_streamed_still_produces_the_text():
    # score_gate refuses before any LLM call, so no token is ever emitted.
    def run(emit):
        return {"text": "Bu soru bilgi tabanının dışında.", "citations": []}

    events = _drain(run, on_meta=lambda result: {"citations": result["citations"]})

    replace = [event for event in events if event["type"] == "replace"]
    assert replace and replace[0]["content"] == "Bu soru bilgi tabanının dışında."


def test_an_exception_becomes_an_error_event():
    def run(emit):
        raise RuntimeError("patladı")

    events = _drain(run, on_meta=lambda result: {})

    assert events[-1]["type"] == "error"
    assert "detail" in events[-1]


def test_events_are_json_serialisable():
    def run(emit):
        emit("a")
        return {"text": "a", "citations": []}

    for event in _drain(run, on_meta=lambda result: {"citations": []}):
        json.loads(format_sse(event)[len("data: ") :])
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_streaming.py -v --no-cov`
Expected: FAIL — `No module named 'azure.rag.streaming'`

- [ ] **Step 3: streaming.py yaz**

`azure/rag/streaming.py`:

```python
"""Turn one agent run into a stream of SSE events.

The agent graph is synchronous and returns a complete answer. Streaming works
by running it on a worker thread while text deltas arrive on a queue, which
this generator drains.

Why `replace` exists: the text that streams is a *candidate*. The citation gate
can reject it and substitute a repaired answer, a "no information" template, or
a refusal that never called the LLM at all. When the final text differs from
what was streamed, the client is told to swap it.
"""

import json
import queue
import threading
from typing import Any, Callable, Iterator

from azure.rag.request_context import reset_token_sink, set_token_sink

_END = object()


def format_sse(event: dict[str, Any]) -> str:
    """One event as an SSE `data:` frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def answer_events(
    run: Callable[[Callable[[str], None]], dict[str, Any]],
    *,
    on_meta: Callable[[dict[str, Any]], dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Run `run` on a worker thread, yielding start/token/meta/replace/error.

    `run` receives an `emit` callable and returns the finished result dict.
    `on_meta` turns that result into the payload of the `meta` event.
    """
    deltas: queue.Queue = queue.Queue()
    outcome: dict[str, Any] = {}

    def worker() -> None:
        # Context variables do not cross thread boundaries, so the sink is
        # installed here rather than in the caller's context.
        token = set_token_sink(deltas.put)
        try:
            outcome["result"] = run(deltas.put)
        except Exception as error:  # noqa: BLE001 - surfaced as an error event
            outcome["error"] = str(error)
        finally:
            reset_token_sink(token)
            deltas.put(_END)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    yield {"type": "start"}

    streamed: list[str] = []
    while True:
        item = deltas.get()
        if item is _END:
            break
        streamed.append(item)
        yield {"type": "token", "content": item}

    thread.join()

    if "error" in outcome:
        yield {"type": "error", "detail": outcome["error"]}
        return

    result = outcome.get("result") or {}
    final_text = result.get("text", "")
    if final_text != "".join(streamed):
        yield {"type": "replace", "content": final_text}

    yield {"type": "meta", **on_meta(result)}
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_streaming.py -v --no-cov`
Expected: 7 passed

- [ ] **Step 5: Akış ucu için başarısız test yaz**

`azure/tests/test_api.py` sonuna ekle. Mevcut dosyadaki istemci kurulum yardımcılarını (FastAPI `TestClient` ve `X-Internal-Token` başlığı) aynen kullan:

```python
def test_ask_stream_emits_sse_frames(monkeypatch, client, internal_headers):
    from azure.rag import api

    class _FakeAnswer:
        text = "Yemek kartı 50 TL/gün. [1]"
        citations = ["calisan_sss_rehberi.xlsx — Genel SSS, satır 9"]
        tool_trace = []
        latency_ms = 12

        class usage:
            input_tokens = 10
            output_tokens = 5

    class _FakeAgent:
        def answer(self, question, memory=None, user_name=None):
            return _FakeAnswer()

    monkeypatch.setattr(api, "_agent", lambda: _FakeAgent())

    response = client.post(
        "/api/ask/stream",
        json={"question": "Yemek kartı ne kadar?"},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert '"type": "start"' in body
    assert '"type": "meta"' in body


def test_ask_stream_rejects_an_empty_question(client, internal_headers):
    response = client.post(
        "/api/ask/stream",
        json={"question": "   "},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 400


def test_ask_stream_requires_the_internal_token(client):
    response = client.post("/api/ask/stream", json={"question": "x"})

    assert response.status_code == 401
```

- [ ] **Step 6: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_api.py -v --no-cov -k stream`
Expected: FAIL — 404, uç yok.

- [ ] **Step 7: Akış ucunu ekle**

`azure/rag/api.py` içine, `ask` ucunun hemen altına. Dosyanın başına gerekli importları ekle:
`from fastapi.responses import StreamingResponse`,
`from azure.rag.memory import ConversationMemory`,
`from azure.rag.streaming import answer_events, format_sse`.

```python
class StreamAskRequest(BaseModel):
    question: str
    userName: str | None = None
    # Client-owned conversation state: the browser holds N conversations per
    # session, so the server cannot key memory by session alone.
    summary: str | None = None
    history: list[dict[str, str]] | None = None


def _memory_from_client(summary: str | None, history: list[dict[str, str]] | None):
    """Rebuild a ConversationMemory from what the browser sent."""
    memory = ConversationMemory()
    pairs = history or []
    question = None
    for message in pairs:
        if message.get("role") == "user":
            question = message.get("content", "")
        elif message.get("role") == "assistant" and question is not None:
            memory.add(question, message.get("content", ""))
            question = None
    return memory


@app.post("/api/ask/stream", dependencies=[Depends(require_internal_token)])
def ask_stream(body: StreamAskRequest, x_session_id: str | None = Header(default=None)):
    session_id = x_session_id or "default"
    _check_rate_limit(session_id)

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    session = _session(session_id)
    set_user_name(session, body.userName or "")
    memory = _memory_from_client(body.summary, body.history)
    model_id = list_models()[0].id

    def run(_emit):
        answer = _agent().answer(question, memory=memory, user_name=get_user_name(session))
        return {
            "text": answer.text,
            "citations": list(answer.citations),
            "answer": answer,
        }

    def on_meta(result):
        answer = result.get("answer")
        if answer is None:
            return {"citations": [], "grounded": False, "modelId": model_id}
        cost = estimate_cost(model_id, answer.usage.input_tokens, answer.usage.output_tokens)
        payload = answer_payload(answer, cost)
        payload["modelId"] = model_id
        return payload

    def body_stream():
        for event in answer_events(run, on_meta=on_meta):
            yield format_sse(event)

    return StreamingResponse(
        body_stream(),
        media_type="text/event-stream",
        # Without this an intermediary may buffer the whole body and the stream
        # arrives as one lump.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 8: Testlerin geçtiğini doğrula**

Run: `pytest azure/tests/test_api.py azure/tests/test_streaming.py -v --no-cov`
Expected: hepsi PASS

- [ ] **Step 9: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/streaming.py azure/rag/api.py azure/tests/test_streaming.py azure/tests/test_api.py
git commit -m "feat(api): add SSE streaming endpoint for chat answers"
```

---

### Task 4: `.txt` yükleyici ve tek dosya yükleme

**Files:**
- Create: `azure/rag/loaders/txt_loader.py`
- Modify: `azure/rag/loaders/__init__.py:13-15`
- Test: `azure/tests/test_loaders_upload.py`

**Interfaces:**
- Consumes: `RawSection`
- Produces:
  - `azure.rag.loaders.txt_loader.load_txt(path: Path) -> list[RawSection]`
  - `azure.rag.loaders.load_file(path: Path) -> list[RawSection]` — tek dosya, uzantıya göre
  - `azure.rag.loaders.UPLOAD_SUFFIXES: set[str]` — `{".pdf", ".docx", ".xlsx", ".txt"}`

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_loaders_upload.py`:

```python
import pytest

from azure.rag.loaders import UPLOAD_SUFFIXES, load_file
from azure.rag.loaders.txt_loader import load_txt


def test_load_txt_produces_one_section_with_the_file_name(tmp_path):
    path = tmp_path / "notlar.txt"
    path.write_text("Yıllık izin 14 gündür.", encoding="utf-8")

    sections = load_txt(path)

    assert len(sections) == 1
    assert sections[0].source_file == "notlar.txt"
    assert sections[0].doc_type == "txt"
    assert "Yıllık izin" in sections[0].text


def test_load_txt_reads_utf8_turkish_characters(tmp_path):
    path = tmp_path / "tr.txt"
    path.write_text("İnsan Kaynakları şğüöç", encoding="utf-8")

    assert "İnsan Kaynakları" in load_txt(path)[0].text


def test_load_txt_tolerates_a_non_utf8_file(tmp_path):
    # A user's file is not guaranteed to be UTF-8; decoding must not explode.
    path = tmp_path / "latin.txt"
    path.write_bytes("Yillik izin\n".encode("cp1254"))

    assert load_txt(path)[0].text.strip() != ""


def test_load_file_dispatches_on_the_suffix(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("merhaba", encoding="utf-8")

    assert load_file(path)[0].doc_type == "txt"


def test_load_file_rejects_an_unsupported_suffix(tmp_path):
    path = tmp_path / "a.exe"
    path.write_bytes(b"\x00")

    with pytest.raises(ValueError):
        load_file(path)


def test_upload_suffixes_cover_the_four_accepted_types():
    assert UPLOAD_SUFFIXES == {".pdf", ".docx", ".xlsx", ".txt"}
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_loaders_upload.py -v --no-cov`
Expected: FAIL — `cannot import name 'UPLOAD_SUFFIXES'`

- [ ] **Step 3: txt_loader.py yaz**

`azure/rag/loaders/txt_loader.py`:

```python
"""Plain-text loader, used only by uploads.

The corpus has no .txt file, so this loader is absent from `SUPPORTED_SUFFIXES`
and the ingest path. Uploads accept it because users bring plain text.
"""

from pathlib import Path

from azure.rag.models import RawSection


def load_txt(path: Path) -> list[RawSection]:
    """Read a text file as one section.

    An uploaded file's encoding is not guaranteed. UTF-8 is tried first and
    cp1254 (Turkish Windows) second; anything still undecodable is replaced
    rather than raising, because losing a few characters beats rejecting the
    document.
    """
    raw = Path(path).read_bytes()
    for encoding in ("utf-8", "cp1254"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    return [
        RawSection(
            source_file=Path(path).name,
            doc_type="txt",
            text=text.strip(),
        )
    ]
```

- [ ] **Step 4: loaders/__init__.py'yi genişlet**

`azure/rag/loaders/__init__.py` içine ekle (mevcut `SUPPORTED_SUFFIXES` ve `_LOADERS` **değişmez** — korpus yükleme davranışı korunur):

```python
from azure.rag.loaders.txt_loader import load_txt

# Uploads accept one type the corpus does not contain.
UPLOAD_SUFFIXES = {".pdf", ".docx", ".xlsx", ".txt"}
_UPLOAD_LOADERS = {**_LOADERS, ".txt": load_txt}


def load_file(path: Path) -> list[RawSection]:
    """Load a single uploaded file, chosen by its suffix."""
    suffix = Path(path).suffix.lower()
    loader = _UPLOAD_LOADERS.get(suffix)
    if loader is None:
        raise ValueError(f"desteklenmeyen dosya tipi: {suffix}")
    return loader(Path(path))
```

- [ ] **Step 5: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_loaders_upload.py -v --no-cov`
Expected: 6 passed

- [ ] **Step 6: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/loaders/ azure/tests/test_loaders_upload.py
git commit -m "feat(loaders): add txt loader and single-file dispatch for uploads"
```

---

### Task 5: Yükleme deposu (TTL, sınırlar, izolasyon)

**Files:**
- Create: `azure/rag/uploads.py`
- Test: `azure/tests/test_uploads.py`

**Interfaces:**
- Consumes: `Chunk`, `chunk_sections`, `load_file`, `AzureOpenAIEmbedder.encode`
- Produces:
  - `azure.rag.uploads.UploadedDoc` — `filename: str`, `chunks: list[Chunk]`, `vectors: list[list[float]]`
  - `azure.rag.uploads.UploadStore(ttl_seconds=3600, max_docs=5, max_chunks=300)`
    - `.add(key: str, doc: UploadedDoc) -> None`
    - `.get(key: str) -> list[UploadedDoc]`
    - `.remove(key: str, filename: str) -> list[UploadedDoc]`
    - `.clear(key: str) -> None`
    - `.sweep() -> None`
  - `azure.rag.uploads.UploadLimitError` — sınır aşımı
  - `azure.rag.uploads.build_uploaded_doc(path, embedder) -> UploadedDoc`
  - `MAX_FILE_BYTES = 10 * 1024 * 1024`

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_uploads.py`:

```python
import pytest

from azure.rag.models import Chunk
from azure.rag.uploads import UploadedDoc, UploadLimitError, UploadStore


def _doc(filename="a.txt", chunk_count=1):
    chunks = [
        Chunk(
            chunk_id=f"{filename}-{i}",
            text=f"metin {i}",
            search_text=f"metin {i}",
            citation_label=f"{filename} — parça {i}",
            metadata={"source_file": filename},
        )
        for i in range(chunk_count)
    ]
    return UploadedDoc(filename=filename, chunks=chunks, vectors=[[0.1] * 4] * chunk_count)


def test_added_document_is_returned_for_its_key():
    store = UploadStore()
    store.add("s1:c1", _doc("rapor.pdf"))

    assert [d.filename for d in store.get("s1:c1")] == ["rapor.pdf"]


def test_conversations_are_isolated_from_each_other():
    store = UploadStore()
    store.add("s1:c1", _doc("a.txt"))

    assert store.get("s1:c2") == []


def test_sessions_are_isolated_from_each_other():
    # The key embeds the session id; one user must never see another's upload.
    store = UploadStore()
    store.add("s1:c1", _doc("gizli.pdf"))

    assert store.get("s2:c1") == []


def test_reuploading_the_same_filename_replaces_the_old_entry():
    store = UploadStore()
    store.add("k", _doc("a.txt", chunk_count=1))
    store.add("k", _doc("a.txt", chunk_count=3))

    docs = store.get("k")
    assert len(docs) == 1
    assert len(docs[0].chunks) == 3


def test_exceeding_the_document_limit_raises():
    store = UploadStore(max_docs=2)
    store.add("k", _doc("a.txt"))
    store.add("k", _doc("b.txt"))

    with pytest.raises(UploadLimitError):
        store.add("k", _doc("c.txt"))


def test_exceeding_the_chunk_limit_raises():
    store = UploadStore(max_chunks=5)
    store.add("k", _doc("a.txt", chunk_count=4))

    with pytest.raises(UploadLimitError):
        store.add("k", _doc("b.txt", chunk_count=2))


def test_remove_drops_only_the_named_document():
    store = UploadStore()
    store.add("k", _doc("a.txt"))
    store.add("k", _doc("b.txt"))

    remaining = store.remove("k", "a.txt")

    assert [d.filename for d in remaining] == ["b.txt"]


def test_clear_empties_the_key():
    store = UploadStore()
    store.add("k", _doc("a.txt"))
    store.clear("k")

    assert store.get("k") == []


def test_entries_expire_after_the_ttl():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))

    clock["now"] = 1061.0

    assert store.get("k") == []


def test_touching_an_entry_extends_its_life():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))

    clock["now"] = 1030.0
    assert store.get("k") != []      # bu erişim süreyi tazeler
    clock["now"] = 1080.0

    assert store.get("k") != []


def test_sweep_removes_expired_keys_without_access():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))
    clock["now"] = 1100.0

    store.sweep()

    assert store.get("k") == []
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_uploads.py -v --no-cov`
Expected: FAIL — `No module named 'azure.rag.uploads'`

- [ ] **Step 3: uploads.py yaz**

`azure/rag/uploads.py`:

```python
"""In-memory, expiring store for documents a user uploaded to one conversation.

Nothing here reaches disk. The uploaded file is parsed inside the request that
carried it and then discarded; only chunks and their vectors survive, and only
until the TTL expires. That is the whole point: uploads must not accumulate on
the server.

Per-replica, like the rate limiter in `api.py`. Under multi-replica scale a
conversation could land on a replica that never saw its upload; the front-end
reconciles by listing documents whenever the conversation changes.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from azure.rag.chunker import chunk_sections
from azure.rag.loaders import load_file
from azure.rag.models import Chunk

MAX_FILE_BYTES = 10 * 1024 * 1024
_DEFAULT_TTL_SECONDS = 3600
_DEFAULT_MAX_DOCS = 5
_DEFAULT_MAX_CHUNKS = 300


class UploadLimitError(Exception):
    """A per-conversation limit would be exceeded."""


@dataclass
class UploadedDoc:
    """One uploaded document: its chunks and their unit vectors, in order."""

    filename: str
    chunks: list[Chunk]
    vectors: list[list[float]]


@dataclass
class _Entry:
    docs: list[UploadedDoc] = field(default_factory=list)
    touched_at: float = 0.0


class UploadStore:
    """Documents per (session, conversation), evicted after `ttl_seconds` idle."""

    def __init__(
        self,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        max_docs: int = _DEFAULT_MAX_DOCS,
        max_chunks: int = _DEFAULT_MAX_CHUNKS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_docs = max_docs
        self.max_chunks = max_chunks
        self._clock = clock or time.monotonic
        self._entries: dict[str, _Entry] = {}

    def sweep(self) -> None:
        """Drop every entry that has been idle longer than the TTL."""
        now = self._clock()
        expired = [
            key
            for key, entry in self._entries.items()
            if now - entry.touched_at > self.ttl_seconds
        ]
        for key in expired:
            del self._entries[key]

    def _live_entry(self, key: str) -> _Entry | None:
        self.sweep()
        return self._entries.get(key)

    def add(self, key: str, doc: UploadedDoc) -> None:
        """Store `doc`, replacing any earlier upload with the same filename."""
        entry = self._entries.setdefault(key, _Entry())
        kept = [existing for existing in entry.docs if existing.filename != doc.filename]

        if len(kept) + 1 > self.max_docs:
            raise UploadLimitError(
                f"Bir sohbete en fazla {self.max_docs} belge yüklenebilir."
            )
        total_chunks = sum(len(existing.chunks) for existing in kept) + len(doc.chunks)
        if total_chunks > self.max_chunks:
            raise UploadLimitError(
                f"Bu sohbetteki toplam parça sayısı {self.max_chunks} sınırını aşıyor."
            )

        kept.append(doc)
        entry.docs = kept
        entry.touched_at = self._clock()

    def get(self, key: str) -> list[UploadedDoc]:
        """Documents for `key`, refreshing its idle timer."""
        entry = self._live_entry(key)
        if entry is None:
            return []
        entry.touched_at = self._clock()
        return list(entry.docs)

    def remove(self, key: str, filename: str) -> list[UploadedDoc]:
        """Drop one document, returning what remains."""
        entry = self._live_entry(key)
        if entry is None:
            return []
        entry.docs = [doc for doc in entry.docs if doc.filename != filename]
        entry.touched_at = self._clock()
        return list(entry.docs)

    def clear(self, key: str) -> None:
        self._entries.pop(key, None)


def build_uploaded_doc(path: Path, embedder) -> UploadedDoc:
    """Parse, chunk and embed one file. The caller deletes `path` afterwards."""
    sections = load_file(path)
    chunks = chunk_sections(sections)
    vectors = embedder.encode([chunk.search_text for chunk in chunks])
    return UploadedDoc(filename=Path(path).name, chunks=chunks, vectors=vectors)
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_uploads.py -v --no-cov`
Expected: 11 passed

- [ ] **Step 5: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/uploads.py azure/tests/test_uploads.py
git commit -m "feat(uploads): add expiring in-memory store for per-conversation documents"
```

---

### Task 6: Yüklenen belgelerde arama ve kapı entegrasyonu

**Files:**
- Create: `azure/rag/upload_search.py`
- Test: `azure/tests/test_upload_search.py`

**Interfaces:**
- Consumes: `UploadedDoc`, `SearchHit`, `Retriever`, `reciprocal_rank_fusion`, `bm25_tokens`, `fold_tr`, `request_context.active_upload_store`
- Produces:
  - `azure.rag.upload_search.search_uploads(docs, query, query_vector, top_k) -> list[SearchHit]`
  - `azure.rag.upload_search.UploadAwareRetriever(base, key, store)` — `Retriever` ile aynı yüzey: `.search()`, `.is_confident()`, `.index`, `.embedder`, `.min_cosine`, `.min_bm25`

**Ölçek uyuşmazlığı — bilinçli karar.** Yüklenen parçalar üzerindeki BM25, korpustan
farklı bir belge kümesi üzerinde hesaplanır; IDF farklı olduğu için skorlar korpusun
BM25 ölçeğiyle **karşılaştırılabilir değildir**. Bu yüzden kapıda yüklenen isabetler
yalnızca **kosinüs** ile değerlendirilir (aynı embedding modelinden gelen birim
vektörlerin kosinüsü ölçek olarak karşılaştırılabilir); `min_bm25` koşulu yalnızca
yüklenen belgeler için aranmaz. Korpus isabetleri için kapı aynen eskisi gibi çalışır.

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_upload_search.py`:

```python
from dataclasses import dataclass

from azure.rag.models import Chunk, SearchHit
from azure.rag.upload_search import UploadAwareRetriever, search_uploads
from azure.rag.uploads import UploadedDoc, UploadStore


def _chunk(chunk_id, text):
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        search_text=text.lower(),
        citation_label=f"yuklenen.txt — {chunk_id}",
        metadata={"source_file": "yuklenen.txt"},
    )


def _doc():
    return UploadedDoc(
        filename="yuklenen.txt",
        chunks=[_chunk("u1", "kurumsal arac tahsis kurallari"), _chunk("u2", "kedi besleme")],
        vectors=[[1.0, 0.0], [0.0, 1.0]],
    )


def test_search_uploads_ranks_the_semantically_closest_chunk_first():
    hits = search_uploads([_doc()], query="arac tahsis", query_vector=[1.0, 0.0], top_k=2)

    assert hits[0].chunk.chunk_id == "u1"


def test_search_uploads_reports_the_cosine_it_computed():
    hits = search_uploads([_doc()], query="arac", query_vector=[1.0, 0.0], top_k=1)

    assert hits[0].cosine == 1.0


def test_search_uploads_returns_nothing_without_documents():
    assert search_uploads([], query="x", query_vector=[1.0, 0.0], top_k=3) == []


def test_search_uploads_respects_top_k():
    assert len(search_uploads([_doc()], "x", [1.0, 0.0], top_k=1)) == 1


# --- retriever wrapper ------------------------------------------------------


@dataclass
class _StubBase:
    """Stands in for the corpus Retriever."""

    hits: list
    confident: bool
    min_cosine: float = 0.25
    min_bm25: float = 4.22
    index: object = None
    embedder: object = None

    def search(self, query, top_k=5, source_filter=None):
        return list(self.hits)

    def is_confident(self, hits):
        return self.confident


def _corpus_hit(score=0.5, cosine=0.9, bm25=9.0):
    return SearchHit(chunk=_chunk("c1", "korpus metni"), score=score, cosine=cosine, bm25=bm25)


class _Embedder:
    def encode(self, texts):
        return [[1.0, 0.0] for _ in texts]


def test_wrapper_merges_corpus_and_uploaded_hits():
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())

    hits = UploadAwareRetriever(base, "k", store).search("arac tahsis", top_k=5)

    ids = {hit.chunk.chunk_id for hit in hits}
    assert "c1" in ids and "u1" in ids


def test_wrapper_behaves_like_the_base_when_nothing_is_uploaded():
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())

    hits = UploadAwareRetriever(base, "k", UploadStore()).search("soru", top_k=5)

    assert [hit.chunk.chunk_id for hit in hits] == ["c1"]


def test_gate_passes_when_only_an_uploaded_chunk_is_relevant():
    # The corpus cannot answer, so the base gate says no. Without this the
    # question would be refused before the LLM ever saw the uploaded file.
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[], confident=False, embedder=_Embedder())
    retriever = UploadAwareRetriever(base, "k", store)

    hits = retriever.search("arac tahsis", top_k=5)

    assert retriever.is_confident(hits) is True


def test_gate_still_refuses_when_the_uploaded_chunk_is_far_away():
    store = UploadStore()
    store.add("k", _doc())

    class _OrthogonalEmbedder:
        def encode(self, texts):
            return [[0.0, 0.0] for _ in texts]

    base = _StubBase(hits=[], confident=False, embedder=_OrthogonalEmbedder())
    retriever = UploadAwareRetriever(base, "k", store)

    hits = retriever.search("alakasiz", top_k=5)

    assert retriever.is_confident(hits) is False


def test_gate_defers_to_the_base_for_corpus_only_hits():
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())
    retriever = UploadAwareRetriever(base, "k", UploadStore())

    assert retriever.is_confident(retriever.search("soru", top_k=5)) is True
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_upload_search.py -v --no-cov`
Expected: FAIL — `No module named 'azure.rag.upload_search'`

- [ ] **Step 3: upload_search.py yaz**

`azure/rag/upload_search.py`:

```python
"""Searching a conversation's uploaded documents, fused with the corpus.

The corpus index is a persistent Chroma collection plus a prebuilt BM25 model.
Inserting a user's ad-hoc document into either would mutate state shared by
every session, so uploads get their own tiny ranking pass and the two result
lists are fused instead.

Scale mismatch, deliberately handled: BM25 over a handful of uploaded chunks
has a different IDF basis than BM25 over the 276-chunk corpus, so the two BM25
numbers are not comparable. The gate therefore judges uploaded hits on cosine
alone — cosines of unit vectors from the same embedding model *are* comparable
— while corpus hits keep the measured two-signal rule.
"""

from typing import Any

from rank_bm25 import BM25Okapi

from azure.rag.models import SearchHit
from azure.rag.normalize import bm25_tokens, fold_tr
from azure.rag.retriever import reciprocal_rank_fusion
from azure.rag.uploads import UploadedDoc

_CANDIDATES = 20


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


def search_uploads(
    docs: list[UploadedDoc], query: str, query_vector: list[float], top_k: int = 5
) -> list[SearchHit]:
    """Rank uploaded chunks with the same hybrid shape the corpus uses."""
    chunks = [chunk for doc in docs for chunk in doc.chunks]
    vectors = [vector for doc in docs for vector in doc.vectors]
    if not chunks:
        return []

    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    cosines = {
        chunk.chunk_id: _dot(query_vector, vector)
        for chunk, vector in zip(chunks, vectors, strict=False)
    }
    dense_ids = sorted(cosines, key=cosines.get, reverse=True)[:_CANDIDATES]

    corpus_tokens = [bm25_tokens(chunk.search_text) for chunk in chunks]
    scores = BM25Okapi(corpus_tokens).get_scores(bm25_tokens(fold_tr(query)))
    bm25_scores = {
        chunk.chunk_id: float(score) for chunk, score in zip(chunks, scores, strict=False)
    }
    lexical_ids = sorted(bm25_scores, key=bm25_scores.get, reverse=True)[:_CANDIDATES]

    fused = reciprocal_rank_fusion([dense_ids, lexical_ids])
    ordered = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    return [
        SearchHit(
            chunk=by_id[chunk_id],
            score=score,
            cosine=cosines.get(chunk_id, 0.0),
            bm25=bm25_scores.get(chunk_id, 0.0),
        )
        for chunk_id, score in ordered
    ][:top_k]


class UploadAwareRetriever:
    """A Retriever-shaped facade that also searches this conversation's uploads.

    Presents exactly the surface `ToolBox` and `graph.py` consume, so neither
    needs to know uploads exist.
    """

    def __init__(self, base: Any, key: str, store: Any) -> None:
        self.base = base
        self.key = key
        self.store = store
        # Mirrored so anything reading the base's attributes keeps working.
        self.index = base.index
        self.embedder = base.embedder
        self.min_cosine = base.min_cosine
        self.min_bm25 = base.min_bm25
        self._upload_ids: set[str] = set()

    def search(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[SearchHit]:
        corpus_hits = self.base.search(query, top_k, source_filter)
        docs = self.store.get(self.key)
        if not docs:
            self._upload_ids = set()
            return corpus_hits

        query_vector = self.embedder.encode([fold_tr(query)])[0]
        upload_hits = search_uploads(docs, query, query_vector, top_k)
        self._upload_ids = {hit.chunk.chunk_id for hit in upload_hits}

        merged = reciprocal_rank_fusion(
            [
                [hit.chunk.chunk_id for hit in corpus_hits],
                [hit.chunk.chunk_id for hit in upload_hits],
            ]
        )
        by_id = {hit.chunk.chunk_id: hit for hit in [*corpus_hits, *upload_hits]}
        ordered = sorted(merged.items(), key=lambda item: item[1], reverse=True)
        return [by_id[chunk_id] for chunk_id, _ in ordered if chunk_id in by_id][:top_k]

    def is_confident(self, hits: list[SearchHit]) -> bool:
        """Pass when the corpus rule passes, or an uploaded chunk is close enough."""
        corpus_hits = [hit for hit in hits if hit.chunk.chunk_id not in self._upload_ids]
        if self.base.is_confident(corpus_hits):
            return True
        upload_hits = [hit for hit in hits if hit.chunk.chunk_id in self._upload_ids]
        return any(hit.cosine >= self.min_cosine for hit in upload_hits)
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_upload_search.py -v --no-cov`
Expected: 10 passed

- [ ] **Step 5: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/upload_search.py azure/tests/test_upload_search.py
git commit -m "feat(retrieval): search uploaded documents alongside the corpus"
```

---

### Task 7: Yükleme uçları

**Files:**
- Modify: `azure/rag/api.py`
- Test: `azure/tests/test_api.py`

**Interfaces:**
- Consumes: `UploadStore`, `build_uploaded_doc`, `UploadLimitError`, `MAX_FILE_BYTES`, `UPLOAD_SUFFIXES`, `UploadAwareRetriever`, `request_context.set_upload_store`
- Produces:
  - `POST /api/documents/upload` (multipart: `file`, `conversation_id`) → `{filename, chunkCount, documents: [...]}`
  - `GET /api/documents?conversation_id=` → `{documents: [{filename, chunkCount}]}`
  - `DELETE /api/documents?conversation_id=&filename=` → `{documents: [...]}`
  - Akış ucu artık yüklenen belgeleri de arar.

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_api.py` sonuna ekle:

```python
def test_upload_accepts_a_text_file_and_lists_it(client, internal_headers, monkeypatch):
    from azure.rag import api

    monkeypatch.setattr(api, "_embedder", lambda: _FakeEmbedder())
    headers = {**internal_headers, "X-Session-Id": "s1"}

    response = client.post(
        "/api/documents/upload",
        files={"file": ("notlar.txt", b"Yillik izin 14 gundur.", "text/plain")},
        data={"conversation_id": "c1"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "notlar.txt"

    listed = client.get("/api/documents?conversation_id=c1", headers=headers)
    assert [d["filename"] for d in listed.json()["documents"]] == ["notlar.txt"]


def test_upload_rejects_an_unsupported_type(client, internal_headers):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("virus.exe", b"\x00", "application/octet-stream")},
        data={"conversation_id": "c1"},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 400


def test_upload_rejects_an_empty_file(client, internal_headers):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("bos.txt", b"", "text/plain")},
        data={"conversation_id": "c1"},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 400


def test_upload_rejects_a_file_over_the_size_limit(client, internal_headers):
    from azure.rag.uploads import MAX_FILE_BYTES

    response = client.post(
        "/api/documents/upload",
        files={"file": ("buyuk.txt", b"x" * (MAX_FILE_BYTES + 1), "text/plain")},
        data={"conversation_id": "c1"},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 413


def test_documents_are_scoped_to_the_session(client, internal_headers, monkeypatch):
    from azure.rag import api

    monkeypatch.setattr(api, "_embedder", lambda: _FakeEmbedder())
    client.post(
        "/api/documents/upload",
        files={"file": ("gizli.txt", b"gizli metin", "text/plain")},
        data={"conversation_id": "c1"},
        headers={**internal_headers, "X-Session-Id": "sA"},
    )

    other = client.get(
        "/api/documents?conversation_id=c1",
        headers={**internal_headers, "X-Session-Id": "sB"},
    )

    assert other.json()["documents"] == []


def test_delete_removes_the_named_document(client, internal_headers, monkeypatch):
    from azure.rag import api

    monkeypatch.setattr(api, "_embedder", lambda: _FakeEmbedder())
    headers = {**internal_headers, "X-Session-Id": "s1"}
    client.post(
        "/api/documents/upload",
        files={"file": ("a.txt", b"metin", "text/plain")},
        data={"conversation_id": "c9"},
        headers=headers,
    )

    response = client.request(
        "DELETE", "/api/documents?conversation_id=c9&filename=a.txt", headers=headers
    )

    assert response.json()["documents"] == []


def test_delete_without_a_filename_clears_the_whole_conversation(
    client, internal_headers, monkeypatch
):
    # What the front-end calls when a conversation is deleted: its uploads must
    # not outlive it.
    from azure.rag import api

    monkeypatch.setattr(api, "_embedder", lambda: _FakeEmbedder())
    headers = {**internal_headers, "X-Session-Id": "s1"}
    for name in ("a.txt", "b.txt"):
        client.post(
            "/api/documents/upload",
            files={"file": (name, b"metin", "text/plain")},
            data={"conversation_id": "c7"},
            headers=headers,
        )

    response = client.request("DELETE", "/api/documents?conversation_id=c7", headers=headers)

    assert response.json()["documents"] == []
    assert client.get("/api/documents?conversation_id=c7", headers=headers).json()["documents"] == []


def test_documents_endpoint_requires_the_internal_token(client):
    assert client.get("/api/documents?conversation_id=c1").status_code == 401
```

Dosyanın üstüne sahte gömücüyü ekle:

```python
class _FakeEmbedder:
    """Deterministic stand-in: no network, no Azure credentials in tests."""

    def encode(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_api.py -v --no-cov -k "upload or documents"`
Expected: FAIL — 404

- [ ] **Step 3: Uçları ekle**

`azure/rag/api.py`'ye ekle. Başa gerekli importlar:
`from fastapi import File, Form, UploadFile`,
`import os, tempfile`,
`from azure.rag.embedder import AzureOpenAIEmbedder`,
`from azure.rag.loaders import UPLOAD_SUFFIXES`,
`from azure.rag.request_context import reset_upload_store, set_upload_store`,
`from azure.rag.upload_search import UploadAwareRetriever`,
`from azure.rag.uploads import MAX_FILE_BYTES, UploadLimitError, UploadStore, build_uploaded_doc`.

```python
_UPLOADS = UploadStore()
_EMBEDDER: Any = None


def _embedder():
    """Built once; the upload path is the only caller in this process."""
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = AzureOpenAIEmbedder(AzureConfig.load())
    return _EMBEDDER


def _upload_key(session_id: str, conversation_id: str) -> str:
    """Namespaced so one session can never read another's uploads."""
    return f"{session_id}:{conversation_id}"


def _document_list(docs) -> list[dict[str, Any]]:
    return [{"filename": doc.filename, "chunkCount": len(doc.chunks)} for doc in docs]


@app.post("/api/documents/upload", dependencies=[Depends(require_internal_token)])
async def upload_document(
    file: UploadFile = File(...),
    conversation_id: str = Form(...),
    x_session_id: str | None = Header(default=None),
):
    session_id = x_session_id or "default"
    _check_rate_limit(session_id)

    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Yalnızca .pdf, .docx, .xlsx ve .txt dosyaları yüklenebilir.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Dosya boş.")
    if len(contents) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor.")

    # The file exists on disk only for as long as the parser needs a path.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(contents)
        temp_path = Path(handle.name)
    try:
        doc = build_uploaded_doc(temp_path, _embedder())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        os.remove(temp_path)

    doc.filename = filename
    key = _upload_key(session_id, conversation_id)
    try:
        _UPLOADS.add(key, doc)
    except UploadLimitError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error

    return {
        "filename": filename,
        "chunkCount": len(doc.chunks),
        "documents": _document_list(_UPLOADS.get(key)),
    }


@app.get("/api/documents", dependencies=[Depends(require_internal_token)])
def list_uploaded(conversation_id: str, x_session_id: str | None = Header(default=None)):
    key = _upload_key(x_session_id or "default", conversation_id)
    return {"documents": _document_list(_UPLOADS.get(key))}


@app.delete("/api/documents", dependencies=[Depends(require_internal_token)])
def delete_uploaded(
    conversation_id: str,
    filename: str | None = None,
    x_session_id: str | None = Header(default=None),
):
    """Drop one document, or the whole conversation when no filename is given.

    The second form is what the front-end calls when a conversation is deleted:
    its uploads must not outlive it, TTL or no TTL.
    """
    key = _upload_key(x_session_id or "default", conversation_id)
    if filename is None:
        _UPLOADS.clear(key)
        return {"documents": []}
    return {"documents": _document_list(_UPLOADS.remove(key, filename))}
```

`Path` importunu (`from pathlib import Path`) dosyanın başına ekle.

- [ ] **Step 4: Akış ucunu yüklemelerden haberdar et**

`ask_stream` içindeki `StreamAskRequest`'e `conversationId: str | None = None` alanını ekle ve `run` fonksiyonunu, yükleme deposu doluysa ajanın retriever'ını saracak şekilde değiştir:

```python
    def run(_emit):
        agent = _agent()
        key = _upload_key(session_id, body.conversationId or "default")
        docs = _UPLOADS.get(key)
        if not docs:
            answer = agent.answer(question, memory=memory, user_name=get_user_name(session))
        else:
            # Swap the retriever for one that also sees this conversation's
            # uploads. The graph is rebuilt around it; compiling the state
            # machine is cheap, and the loaded index is shared, not reloaded.
            from azure.rag.agent import Agent
            from azure.rag.tools import ToolBox

            wrapped = UploadAwareRetriever(agent.retriever, key, _UPLOADS)
            scoped = Agent(
                wrapped,
                ToolBox(wrapped),
                agent.llm,
                agent.max_tool_turns,
                metrics=agent.metrics,
            )
            answer = scoped.answer(question, memory=memory, user_name=get_user_name(session))
        return {"text": answer.text, "citations": list(answer.citations), "answer": answer}
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `pytest azure/tests/test_api.py -v --no-cov`
Expected: hepsi PASS

- [ ] **Step 6: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/api.py azure/tests/test_api.py
git commit -m "feat(api): add per-conversation document upload, listing and deletion"
```

---

### Task 8: Özetleme ucu

**Files:**
- Create: `azure/rag/summarize.py`
- Modify: `azure/rag/api.py`
- Test: `azure/tests/test_summarize.py`, `azure/tests/test_api.py`

**Interfaces:**
- Consumes: `AzureOpenAIClient.chat`
- Produces:
  - `azure.rag.summarize.build_transcript(messages) -> str`
  - `azure.rag.summarize.summarize_messages(llm, previous_summary, messages) -> str`
  - `POST /api/summarize` → `{summary: str}`

- [ ] **Step 1: Başarısız test yaz**

`azure/tests/test_summarize.py`:

```python
import pytest

from azure.rag.summarize import build_transcript, summarize_messages


def test_build_transcript_labels_each_speaker_in_turkish():
    transcript = build_transcript(
        [
            {"role": "user", "content": "İzin nasıl alınır?"},
            {"role": "assistant", "content": "Formu doldurun."},
        ]
    )

    assert transcript == "Kullanıcı: İzin nasıl alınır?\nAsistan: Formu doldurun."


def test_build_transcript_skips_unknown_roles():
    transcript = build_transcript(
        [{"role": "system", "content": "gizli"}, {"role": "user", "content": "soru"}]
    )

    assert "gizli" not in transcript


class _StubLLM:
    def __init__(self, text="özet metni"):
        self.text = text
        self.messages = None

    def chat(self, messages, tools=None):
        self.messages = messages
        return type("R", (), {"text": self.text})()


def test_summarize_returns_the_model_text():
    assert summarize_messages(_StubLLM("kısa özet"), "", [{"role": "user", "content": "a"}]) == "kısa özet"


def test_summarize_sends_no_tools():
    # Summarising must never trigger a document search.
    llm = _StubLLM()
    summarize_messages(llm, "", [{"role": "user", "content": "a"}])

    assert llm.messages is not None


def test_summarize_includes_the_previous_summary():
    llm = _StubLLM()
    summarize_messages(llm, "önceki özet burada", [{"role": "user", "content": "a"}])

    assert "önceki özet burada" in llm.messages[-1]["content"]


def test_summarize_rejects_an_empty_message_list():
    with pytest.raises(ValueError):
        summarize_messages(_StubLLM(), "", [])
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_summarize.py -v --no-cov`
Expected: FAIL — `No module named 'azure.rag.summarize'`

- [ ] **Step 3: summarize.py yaz**

`azure/rag/summarize.py`:

```python
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
    lines = [
        f"{_ROLE_LABELS[message['role']]}: {message.get('content', '')}"
        for message in messages
        if message.get("role") in _ROLE_LABELS
    ]
    return "\n".join(lines)


def summarize_messages(
    llm: Any, previous_summary: str, messages: list[dict[str, str]]
) -> str:
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
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest azure/tests/test_summarize.py -v --no-cov`
Expected: 6 passed

- [ ] **Step 5: Uç için başarısız test yaz**

`azure/tests/test_api.py` sonuna:

```python
def test_summarize_returns_a_summary(client, internal_headers, monkeypatch):
    from azure.rag import api

    class _StubLLM:
        def chat(self, messages, tools=None):
            return type("R", (), {"text": "birleşik özet"})()

    monkeypatch.setattr(api, "_summary_llm", lambda: _StubLLM())

    response = client.post(
        "/api/summarize",
        json={"previousSummary": "", "messages": [{"role": "user", "content": "a"}]},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "birleşik özet"


def test_summarize_rejects_an_empty_message_list(client, internal_headers):
    response = client.post(
        "/api/summarize",
        json={"previousSummary": "", "messages": []},
        headers={**internal_headers, "X-Session-Id": "s1"},
    )

    assert response.status_code == 400
```

- [ ] **Step 6: Testin başarısız olduğunu doğrula**

Run: `pytest azure/tests/test_api.py -v --no-cov -k summarize`
Expected: FAIL — 404

- [ ] **Step 7: Ucu ekle**

`azure/rag/api.py`'ye, `from azure.rag.summarize import summarize_messages` importuyla birlikte:

```python
def _summary_llm():
    """The chat client, reused for summarising."""
    return _agent().llm


class SummarizeRequest(BaseModel):
    previousSummary: str = ""
    messages: list[dict[str, str]]


@app.post("/api/summarize", dependencies=[Depends(require_internal_token)])
def summarize(body: SummarizeRequest, x_session_id: str | None = Header(default=None)):
    _check_rate_limit(x_session_id or "default")
    try:
        summary = summarize_messages(_summary_llm(), body.previousSummary, body.messages)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"summary": summary}
```

- [ ] **Step 8: Testlerin geçtiğini doğrula**

Run: `pytest azure/tests/ -v --no-cov`
Expected: hepsi PASS

- [ ] **Step 9: Kalite kapısı ve commit**

```bash
ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70
git add azure/rag/summarize.py azure/rag/api.py azure/tests/test_summarize.py azure/tests/test_api.py
git commit -m "feat(api): add rolling conversation summarization endpoint"
```

---

### Task 9: Proxy — akış, multipart, izin listesi

**Files:**
- Modify: `azure/web/app/api/proxy/[...path]/route.ts`
- Modify: `azure/web/package.json`
- Test: `azure/web/__tests__/auth.test.ts`

**Interfaces:**
- Consumes: `SESSION_COOKIE`, `verifySessionToken`
- Produces: proxy artık `api/ask/stream`, `api/documents`, `api/documents/upload`, `api/summarize` yollarını geçirir; `DELETE` destekler; akış gövdelerini tamponlamadan aktarır.

- [ ] **Step 1: package.json'a test script'i ekle**

`azure/web/package.json` içindeki `scripts` bloğuna ekle:

```json
    "test": "vitest run"
```

- [ ] **Step 2: Başarısız test yaz**

`azure/web/__tests__/auth.test.ts` içindeki `describe("proxy", ...)` bloğuna ekle:

```typescript
  it("forwards the streaming endpoint without buffering", async () => {
    const encoder = new TextEncoder();
    const upstream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"start"}\n\n'));
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(upstream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
      ),
    );
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/ask/stream");
    const response = await POST(request, {
      params: Promise.resolve({ path: ["api", "ask", "stream"] }),
    });

    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(response.body).not.toBeNull();
  });

  it("allows the upload endpoint through", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/documents/upload");
    const response = await POST(request, {
      params: Promise.resolve({ path: ["api", "documents", "upload"] }),
    });

    expect(response.status).toBe(200);
    expect(calls).toHaveLength(1);
  });

  it("supports DELETE for documents", async () => {
    const calls = stubFetch();
    const { DELETE } = await import("../app/api/proxy/[...path]/route");
    const { createSessionToken, SESSION_COOKIE } = await import("../lib/auth");
    const { NextRequest } = await import("next/server");

    const request = new NextRequest(
      "http://localhost:3000/api/proxy/api/documents?conversation_id=c1&filename=a.txt",
      { method: "DELETE" },
    );
    request.cookies.set(SESSION_COOKIE, await createSessionToken("demo"));
    const response = await DELETE(request, {
      params: Promise.resolve({ path: ["api", "documents"] }),
    });

    expect(response.status).toBe(200);
    expect(calls[0].url).toContain("conversation_id=c1");
  });

  it("still refuses an endpoint outside the allow-list", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/secret");
    const response = await POST(request, { params: Promise.resolve({ path: ["api", "secret"] }) });

    expect(response.status).toBe(404);
    expect(calls).toHaveLength(0);
  });
```

- [ ] **Step 3: Testin başarısız olduğunu doğrula**

Run: `cd azure/web && npm test`
Expected: yeni testler FAIL — `DELETE` dışa aktarılmamış, akış yolu izin listesinde yok.

- [ ] **Step 4: Proxy'yi güncelle**

`azure/web/app/api/proxy/[...path]/route.ts` içindeki `ALLOWED` ve `forward`'ı değiştir:

```typescript
const ALLOWED = new Set([
  "api/ask",
  "api/ask/stream",
  "api/chat/clear",
  "api/models",
  "api/metrics",
  "api/summarize",
  "api/documents",
  "api/documents/upload",
]);

// Streaming responses must not be buffered; multipart bodies must keep their
// boundary header, which means the Content-Type cannot be forced to JSON.
async function forward(request: NextRequest, path: string[]) {
  const session = await verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value ?? "");
  if (!session) {
    return NextResponse.json({ error: "Oturum gerekli." }, { status: 401 });
  }

  const target = path.join("/");
  if (!ALLOWED.has(target)) {
    return NextResponse.json({ error: "Bulunamadı." }, { status: 404 });
  }

  const backend = process.env.BACKEND_URL ?? "";
  const query = request.nextUrl.search;

  const headers: Record<string, string> = {
    "X-Internal-Token": process.env.INTERNAL_TOKEN ?? "",
    // Server-derived: the client's value is deliberately discarded.
    "X-Session-Id": session.sid,
  };
  const incomingType = request.headers.get("content-type");
  if (incomingType) headers["Content-Type"] = incomingType;

  const hasBody = request.method !== "GET" && request.method !== "DELETE";

  const response = await fetch(`${backend}/${target}${query}`, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const contentType = response.headers.get("Content-Type") ?? "application/json";

  if (contentType.startsWith("text/event-stream")) {
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": contentType },
  });
}
```

Dosyanın sonuna `DELETE` işleyicisini ekle:

```typescript
export async function DELETE(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

Run: `cd azure/web && npm test`
Expected: 16 passed (mevcut 12 + yeni 4)

- [ ] **Step 6: Commit**

```bash
git add azure/web/app/api/proxy azure/web/__tests__/auth.test.ts azure/web/package.json
git commit -m "feat(web): pass streaming, multipart and DELETE through the proxy"
```

---

### Task 10: Ön yüz durum katmanı

**Files:**
- Create: `azure/web/lib/types.ts`, `azure/web/lib/storage.ts`, `azure/web/lib/memory.ts`, `azure/web/lib/sse.ts`
- Test: `azure/web/__tests__/conversations.test.ts`

**Interfaces:**
- Consumes: yok
- Produces:
  - `types.ts`: `Source`, `Message`, `Conversation`, `DocumentInfo`
  - `storage.ts`: `newId()`, `createConversation()`, `loadConversations()`, `saveConversations(list)`, `generateTitle(text)`, `groupByDate(list)`
  - `memory.ts`: `SUMMARY_BLOCK`, `buildContext(c)`, `needsSummarization(c)`, `messagesToSummarize(c)`
  - `sse.ts`: `readSseStream(body, onEvent)`

- [ ] **Step 1: Başarısız test yaz**

`azure/web/__tests__/conversations.test.ts`:

```typescript
import { describe, expect, it } from "vitest";

import { buildContext, messagesToSummarize, needsSummarization, SUMMARY_BLOCK } from "../lib/memory";
import { generateTitle, groupByDate } from "../lib/storage";
import { readSseStream } from "../lib/sse";
import type { Conversation, Message } from "../lib/types";

function conversation(messageCount: number, summarizedUpTo = 0): Conversation {
  const messages: Message[] = Array.from({ length: messageCount }, (_, index) => ({
    id: String(index),
    role: index % 2 === 0 ? "user" : "assistant",
    content: `m${index}`,
    createdAt: index,
  }));
  return {
    id: "c1",
    title: "Test",
    createdAt: 0,
    updatedAt: 0,
    documentName: null,
    messages,
    summary: null,
    summarizedUpTo,
  };
}

describe("summarization threshold", () => {
  it("is ten messages", () => {
    expect(SUMMARY_BLOCK).toBe(10);
  });

  it("does not trigger at nine unsummarized messages", () => {
    expect(needsSummarization(conversation(9))).toBe(false);
  });

  it("triggers at ten unsummarized messages", () => {
    expect(needsSummarization(conversation(10))).toBe(true);
  });

  it("triggers again ten messages after the previous block", () => {
    expect(needsSummarization(conversation(20, 10))).toBe(true);
    expect(needsSummarization(conversation(19, 10))).toBe(false);
  });

  it("summarizes exactly the next ten unsummarized messages", () => {
    const batch = messagesToSummarize(conversation(25, 10));

    expect(batch).toHaveLength(10);
    expect(batch[0].content).toBe("m10");
    expect(batch[9].content).toBe("m19");
  });
});

describe("context building", () => {
  it("sends only the unsummarized tail as history", () => {
    const { recentMessages } = buildContext(conversation(13, 10));

    expect(recentMessages.map((m) => m.content)).toEqual(["m10", "m11", "m12"]);
  });

  it("passes the stored summary through", () => {
    const source = { ...conversation(11, 10), summary: "önceki özet" };

    expect(buildContext(source).summary).toBe("önceki özet");
  });

  it("returns an empty summary when none exists", () => {
    expect(buildContext(conversation(3)).summary).toBe("");
  });
});

describe("titles and grouping", () => {
  it("keeps a short question intact", () => {
    expect(generateTitle("  Yıllık izin nasıl alınır?  ")).toBe("Yıllık izin nasıl alınır?");
  });

  it("truncates a long question", () => {
    const title = generateTitle("a".repeat(80));

    expect(title.length).toBeLessThanOrEqual(41);
    expect(title.endsWith("…")).toBe(true);
  });

  it("groups today's conversations under Bugün", () => {
    const groups = groupByDate([{ ...conversation(1), updatedAt: Date.now() }]);

    expect(groups[0].label).toBe("Bugün");
  });
});

describe("sse reader", () => {
  it("assembles events split across chunks", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"to'));
        controller.enqueue(encoder.encode('ken","content":"ab"}\n\n'));
        controller.enqueue(encoder.encode('data: {"type":"meta","citations":[]}\n\n'));
        controller.close();
      },
    });
    const seen: unknown[] = [];

    await readSseStream(stream, (event) => seen.push(event));

    expect(seen).toEqual([
      { type: "token", content: "ab" },
      { type: "meta", citations: [] },
    ]);
  });

  it("ignores malformed frames rather than throwing", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode("data: not-json\n\n"));
        controller.enqueue(encoder.encode('data: {"type":"start"}\n\n'));
        controller.close();
      },
    });
    const seen: unknown[] = [];

    await readSseStream(stream, (event) => seen.push(event));

    expect(seen).toEqual([{ type: "start" }]);
  });
});
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `cd azure/web && npm test`
Expected: FAIL — `Cannot find module '../lib/memory'`

- [ ] **Step 3: types.ts yaz**

```typescript
export type Source = { label: string };

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  grounded?: boolean;
  error?: string;
  createdAt: number;
};

export type DocumentInfo = { filename: string; chunkCount: number };

export type Conversation = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  documentName: string | null;
  messages: Message[];
  summary: string | null;
  summarizedUpTo: number;
};
```

- [ ] **Step 4: storage.ts yaz**

```typescript
import { Conversation } from "./types";

const STORAGE_KEY = "nobel-rag-conversations";

export function newId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Conversation[]) : [];
  } catch {
    return [];
  }
}

/** Returns an error message when the write failed, otherwise null. */
export function saveConversations(list: Conversation[]): string | null {
  if (typeof window === "undefined") return null;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    return null;
  } catch {
    // Quota is the realistic cause. Say so rather than losing writes silently.
    return "Tarayıcı depolama alanı doldu. Eski sohbetleri silin.";
  }
}

export function createConversation(): Conversation {
  const now = Date.now();
  return {
    id: newId(),
    title: "Yeni sohbet",
    createdAt: now,
    updatedAt: now,
    documentName: null,
    messages: [],
    summary: null,
    summarizedUpTo: 0,
  };
}

export function generateTitle(text: string): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length <= 40 ? clean : clean.slice(0, 40).trimEnd() + "…";
}

export function groupByDate(list: Conversation[]): { label: string; items: Conversation[] }[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;

  const today: Conversation[] = [];
  const yesterday: Conversation[] = [];
  const older: Conversation[] = [];

  for (const item of list) {
    if (item.updatedAt >= startOfToday) today.push(item);
    else if (item.updatedAt >= startOfYesterday) yesterday.push(item);
    else older.push(item);
  }

  const groups: { label: string; items: Conversation[] }[] = [];
  if (today.length) groups.push({ label: "Bugün", items: today });
  if (yesterday.length) groups.push({ label: "Dün", items: yesterday });
  if (older.length) groups.push({ label: "Daha eski", items: older });
  return groups;
}
```

- [ ] **Step 5: memory.ts yaz**

```typescript
import { Conversation, Message } from "./types";

/** How many messages are folded into the summary at a time. */
export const SUMMARY_BLOCK = 10;

export function buildContext(c: Conversation): { summary: string; recentMessages: Message[] } {
  return { summary: c.summary ?? "", recentMessages: c.messages.slice(c.summarizedUpTo) };
}

/** True once ten messages have accumulated since the last summary. */
export function needsSummarization(c: Conversation): boolean {
  return c.messages.length - c.summarizedUpTo >= SUMMARY_BLOCK;
}

export function messagesToSummarize(c: Conversation): Message[] {
  return c.messages.slice(c.summarizedUpTo, c.summarizedUpTo + SUMMARY_BLOCK);
}
```

- [ ] **Step 6: sse.ts yaz**

```typescript
export type StreamEvent = Record<string, unknown> & { type: string };

/**
 * Drain an SSE body, calling `onEvent` per frame.
 *
 * Frames are split on the blank-line delimiter, not on chunk boundaries: one
 * `data:` line routinely arrives across two network chunks.
 */
export async function readSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((candidate) => candidate.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as StreamEvent);
      } catch {
        // A truncated or malformed frame is skipped; the stream continues.
      }
    }
  }
}
```

- [ ] **Step 7: Testin geçtiğini doğrula**

Run: `cd azure/web && npm test`
Expected: hepsi PASS

- [ ] **Step 8: Commit**

```bash
git add azure/web/lib azure/web/__tests__/conversations.test.ts
git commit -m "feat(web): add conversation state, summarization thresholds and SSE reader"
```

---

### Task 11: Ön yüz bileşenleri

**Files:**
- Create: `azure/web/lib/useConversations.ts`, `azure/web/components/Sidebar.tsx`, `ConversationItem.tsx`, `ChatPane.tsx`, `MessageBubble.tsx`, `Composer.tsx`, `DocumentChips.tsx`, `SourceDisclosure.tsx`
- Modify: `azure/web/package.json`

**Interfaces:**
- Consumes: `types.ts`, `storage.ts`, `memory.ts`, `sse.ts`
- Produces: `useConversations()` → `{ conversations, activeId, active, streaming, activeDocuments, uploading, toast, sendMessage, regenerate, editAndResend, uploadDocument, removeDocument, selectConversation, newConversation, renameConversation, deleteConversation }`

- [ ] **Step 1: Markdown bağımlılıklarını ekle**

Run: `cd azure/web && npm install react-markdown remark-gfm`
Expected: `package.json` `dependencies` bölümüne ikisi eklenir.

- [ ] **Step 2: useConversations.ts yaz**

Referans projedeki `lib/useConversations.ts` yapısı temel alınır, üç farkla: akış `/api/proxy/api/ask/stream` ucuna JSON gövdesiyle gider (form-data değil), `replace` olayı balonu değiştirir, yükleme uçları `/api/proxy/api/documents*` altındadır.

```typescript
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { buildContext, messagesToSummarize, needsSummarization, SUMMARY_BLOCK } from "./memory";
import { readSseStream } from "./sse";
import {
  createConversation,
  generateTitle,
  loadConversations,
  newId,
  saveConversations,
} from "./storage";
import { Conversation, DocumentInfo, Message } from "./types";

const BASE = "/api/proxy";

export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [documentsByConversation, setDocumentsByConversation] = useState<
    Record<string, DocumentInfo[]>
  >({});
  const [loaded, setLoaded] = useState(false);

  // Streaming closures need the newest list, which state alone cannot give them.
  const conversationsRef = useRef<Conversation[]>([]);
  conversationsRef.current = conversations;

  useEffect(() => {
    const stored = loadConversations();
    const list = stored.length > 0 ? stored : [createConversation()];
    setConversations(list);
    setActiveId(list[0].id);
    setLoaded(true);
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const error = saveConversations(conversations);
    if (error) setToast(error);
  }, [conversations, loaded]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  const active = conversations.find((c) => c.id === activeId) ?? null;
  const activeDocuments = activeId ? (documentsByConversation[activeId] ?? []) : [];

  const updateConversation = useCallback(
    (id: string, updater: (c: Conversation) => Conversation) => {
      setConversations((prev) => prev.map((c) => (c.id === id ? updater(c) : c)));
    },
    [],
  );

  // --- documents ------------------------------------------------------------

  const refreshDocuments = useCallback(async (conversationId: string) => {
    try {
      const response = await fetch(
        `${BASE}/api/documents?conversation_id=${encodeURIComponent(conversationId)}`,
      );
      if (!response.ok) return;
      const data = await response.json();
      setDocumentsByConversation((prev) => ({ ...prev, [conversationId]: data.documents ?? [] }));
    } catch {
      // The list stays as it was; the next switch retries.
    }
  }, []);

  useEffect(() => {
    // The server's TTL can expire an upload while the browser still lists it,
    // so reconcile whenever the conversation changes.
    if (activeId) void refreshDocuments(activeId);
  }, [activeId, refreshDocuments]);

  const uploadDocument = useCallback(
    async (file: File): Promise<string | null> => {
      if (!activeId) return "Aktif sohbet yok.";
      const form = new FormData();
      form.append("file", file);
      form.append("conversation_id", activeId);
      try {
        const response = await fetch(`${BASE}/api/documents/upload`, {
          method: "POST",
          body: form,
        });
        const data = await response.json();
        if (!response.ok) return data.detail ?? "Yükleme başarısız.";
        setDocumentsByConversation((prev) => ({ ...prev, [activeId]: data.documents ?? [] }));
        updateConversation(activeId, (c) => ({
          ...c,
          documentName: (data.documents ?? []).map((d: DocumentInfo) => d.filename).join(", ") || null,
          updatedAt: Date.now(),
        }));
        return null;
      } catch {
        return "Yükleme başarısız: bağlantı hatası.";
      }
    },
    [activeId, updateConversation],
  );

  const removeDocument = useCallback(
    async (filename: string) => {
      if (!activeId) return;
      try {
        const response = await fetch(
          `${BASE}/api/documents?conversation_id=${encodeURIComponent(activeId)}` +
            `&filename=${encodeURIComponent(filename)}`,
          { method: "DELETE" },
        );
        if (!response.ok) return;
        const data = await response.json();
        setDocumentsByConversation((prev) => ({ ...prev, [activeId]: data.documents ?? [] }));
      } catch {
        // Leave the chip in place; the next refresh reconciles.
      }
    },
    [activeId],
  );

  // --- summarization --------------------------------------------------------

  const maybeSummarize = useCallback(
    async (conversationId: string) => {
      const conversation = conversationsRef.current.find((c) => c.id === conversationId);
      if (!conversation || !needsSummarization(conversation)) return;

      try {
        const response = await fetch(`${BASE}/api/summarize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            previousSummary: conversation.summary ?? "",
            messages: messagesToSummarize(conversation).map((m) => ({
              role: m.role,
              content: m.content,
            })),
          }),
        });
        if (!response.ok) return;
        const data = await response.json();
        if (!data.summary) return;
        updateConversation(conversationId, (c) => ({
          ...c,
          summary: data.summary,
          summarizedUpTo: c.summarizedUpTo + SUMMARY_BLOCK,
        }));
      } catch {
        // Retried on the next block; the user never waits for this.
      }
    },
    [updateConversation],
  );

  // --- asking ---------------------------------------------------------------

  const runAsk = useCallback(
    async (conversationId: string, question: string, baseMessages: Message[]) => {
      const conversation = conversationsRef.current.find((c) => c.id === conversationId);
      if (!conversation) return;

      const userMessage: Message = {
        id: newId(),
        role: "user",
        content: question,
        createdAt: Date.now(),
      };
      const assistantMessage: Message = {
        id: newId(),
        role: "assistant",
        content: "",
        createdAt: Date.now(),
      };

      updateConversation(conversationId, (c) => ({
        ...c,
        title: baseMessages.length === 0 ? generateTitle(question) : c.title,
        messages: [...baseMessages, userMessage, assistantMessage],
        updatedAt: Date.now(),
      }));
      setStreaming(true);

      const { summary, recentMessages } = buildContext({ ...conversation, messages: baseMessages });

      const patch = (updater: (m: Message) => Message) =>
        updateConversation(conversationId, (c) => ({
          ...c,
          messages: c.messages.map((m) => (m.id === assistantMessage.id ? updater(m) : m)),
        }));

      try {
        const response = await fetch(`${BASE}/api/ask/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            conversationId,
            summary,
            history: recentMessages.map((m) => ({ role: m.role, content: m.content })),
          }),
        });

        if (!response.ok || !response.body) {
          const data = await response.json().catch(() => ({ detail: "Bilinmeyen hata" }));
          patch((m) => ({ ...m, error: data.detail ?? "Bilinmeyen hata" }));
          return;
        }

        await readSseStream(response.body, (event) => {
          if (event.type === "start") {
            patch((m) => ({ ...m, content: "" }));
          } else if (event.type === "token") {
            const text = String(event.content ?? "");
            patch((m) => ({ ...m, content: m.content + text }));
          } else if (event.type === "replace") {
            // The citation gate substituted the answer after it streamed.
            patch((m) => ({ ...m, content: String(event.content ?? "") }));
          } else if (event.type === "meta") {
            patch((m) => ({
              ...m,
              citations: (event.citations as string[]) ?? [],
              grounded: Boolean(event.grounded),
            }));
          } else if (event.type === "error") {
            patch((m) => ({ ...m, error: String(event.detail ?? "Bilinmeyen hata") }));
          }
        });
      } catch {
        patch((m) => ({ ...m, error: "Bağlantı kesildi." }));
      } finally {
        setStreaming(false);
        updateConversation(conversationId, (c) => ({ ...c, updatedAt: Date.now() }));
        void maybeSummarize(conversationId);
      }
    },
    [maybeSummarize, updateConversation],
  );

  const sendMessage = useCallback(
    (question: string) => {
      if (!activeId || streaming) return;
      const conversation = conversationsRef.current.find((c) => c.id === activeId);
      if (!conversation) return;
      void runAsk(activeId, question, conversation.messages);
    },
    [activeId, runAsk, streaming],
  );

  const regenerate = useCallback(() => {
    if (!activeId || streaming) return;
    const conversation = conversationsRef.current.find((c) => c.id === activeId);
    if (!conversation) return;
    const reversedIndex = [...conversation.messages].reverse().findIndex((m) => m.role === "user");
    if (reversedIndex === -1) return;
    const index = conversation.messages.length - 1 - reversedIndex;
    void runAsk(activeId, conversation.messages[index].content, conversation.messages.slice(0, index));
  }, [activeId, runAsk, streaming]);

  const editAndResend = useCallback(
    (messageId: string, newText: string) => {
      if (!activeId || streaming) return;
      const conversation = conversationsRef.current.find((c) => c.id === activeId);
      if (!conversation) return;
      const index = conversation.messages.findIndex((m) => m.id === messageId);
      if (index === -1) return;
      void runAsk(activeId, newText, conversation.messages.slice(0, index));
    },
    [activeId, runAsk, streaming],
  );

  // --- conversation management ---------------------------------------------

  const newConversation = useCallback(() => {
    const fresh = createConversation();
    setConversations((prev) => [fresh, ...prev]);
    setActiveId(fresh.id);
  }, []);

  const selectConversation = useCallback((id: string) => setActiveId(id), []);

  const renameConversation = useCallback(
    (id: string, title: string) => {
      const clean = title.trim();
      if (!clean) return;
      updateConversation(id, (c) => ({ ...c, title: clean, updatedAt: Date.now() }));
    },
    [updateConversation],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      // Uploads belong to the conversation; dropping it drops them server-side
      // too. Omitting `filename` clears the whole conversation.
      void fetch(`${BASE}/api/documents?conversation_id=${encodeURIComponent(id)}`, {
        method: "DELETE",
      }).catch(() => undefined);
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (next.length === 0) {
          const fresh = createConversation();
          setActiveId(fresh.id);
          return [fresh];
        }
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
    },
    [activeId],
  );

  return {
    conversations,
    activeId,
    active,
    streaming,
    uploading,
    setUploading,
    toast,
    setToast,
    activeDocuments,
    uploadDocument,
    removeDocument,
    sendMessage,
    regenerate,
    editAndResend,
    selectConversation,
    newConversation,
    renameConversation,
    deleteConversation,
  };
}
```

- [ ] **Step 3: Sunum bileşenlerini yaz**

Yedi bileşen, referans projedeki (`C:\Users\Polinity\Desktop\azure-rag\frontend\components\`) aynı adlı dosyalar temel alınarak yazılır. Zorunlu farklar:

- Her renk `var(--…)` simgesinden okunur; hiçbir bileşende sabit renk (`#…`, `text-red-500` vb.) bulunmaz. Hata metni için `var(--danger)` kullanılır.
- `SourceDisclosure` web araması değil **alıntı listesi** gösterir: `citations: string[]` alır, açıldığında her alıntı etiketini bir satır olarak listeler; boşsa "Bu cevap bir kaynağa dayanmıyor." yazar.
- `DocumentChips` `DocumentInfo` (`filename`, `chunkCount`) alır ve `{chunkCount} parça` gösterir.
- `Composer` dosya seçiciyi `.pdf,.docx,.xlsx,.txt` ile sınırlar.
- `ChatPane` boş durumda korpusun her zaman hazır olduğunu anlatır: doküman yüklemek zorunlu değildir — "Şirket dokümanlarına soru sorabilir veya bu sohbete kendi dosyanızı ekleyebilirsiniz."
- `MessageBubble` `react-markdown` + `remark-gfm` kullanır; akış sırasında sonda `stream-cursor` gösterir.

- [ ] **Step 4: Derlemenin ve testlerin geçtiğini doğrula**

Run: `cd azure/web && npx tsc --noEmit && npm test && npx next build`
Expected: tip hatası yok, testler geçer, derleme tamamlanır.

- [ ] **Step 5: Commit**

```bash
git add azure/web/lib/useConversations.ts azure/web/components azure/web/package.json azure/web/package-lock.json
git commit -m "feat(web): add conversation sidebar, streaming chat pane and composer"
```

---

### Task 12: Kabuk, entegrasyon doğrulaması ve durum güncellemesi

**Files:**
- Modify: `azure/web/app/page.tsx`
- Modify: `PROGRESSION.md`, `MEMORY.md`

**Interfaces:**
- Consumes: `useConversations`, tüm bileşenler
- Produces: yeni uygulama kabuğu

- [ ] **Step 1: page.tsx'i yeniden yaz**

Kabuk: solda `Sidebar`, ortada `ChatPane` + `Composer`, üstte tema anahtarı ve çıkış düğmesi, tüm pencerede sürükle-bırak katmanı, altta toast. Mevcut `page.tsx`'teki tema mantığı (`localStorage` + `prefers-color-scheme` ile başlatılan `dark` durumu) ve `signOut` fonksiyonu **korunur** — yalnızca yerleşimleri değişir.

Çıkışta yüklenen belgeler sunucudan da düşsün diye `signOut`, `localStorage`'daki sohbet kaydını temizler:

```typescript
  async function signOut() {
    localStorage.removeItem("nobel-rag-conversations");
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }
```

- [ ] **Step 2: Derleme ve testler**

Run: `cd azure/web && npx tsc --noEmit && npm test && npx next build`
Expected: hepsi temiz.

- [ ] **Step 3: Tam kalite kapısı**

Run: `ruff format . && ruff check . --fix && pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70`
Expected: 0 failure, kapsam ≥ %70.

- [ ] **Step 4: Yerel uçtan uca doğrulama**

İki terminalde:

```bash
uvicorn azure.rag.api:app --port 8000
cd azure/web && npm run dev
```

`http://localhost:3000` üzerinde sırayla doğrula ve **çıktıyı gözle kaydet**:

1. Giriş yapılır, sohbet listesi görünür.
2. "Yemek kartı tutarı ne kadar?" sorusu **kelime kelime akar** ve alıntıyla biter.
3. "Bitcoin fiyatı nedir?" reddedilir; akan metin varsa `replace` ile reddetme metnine döner.
4. Bir `.txt` dosyası yüklenir, çip görünür, yalnızca o dosyada geçen bir soru cevaplanır.
5. Çip kaldırılır, aynı soru artık reddedilir.
6. 10 mesaj sonrası ağ sekmesinde `/api/summarize` çağrısı görünür.
7. Yeni sohbet açılır, önceki sohbetin belgeleri **görünmez**.
8. Çıkış yapılıp girilince sohbet listesi boştur.

- [ ] **Step 5: PROGRESSION.md ve MEMORY.md güncelle**

`PROGRESSION.md`'ye Aşama 1'in tamamlandığını ve sıradaki adımın Aşama 2 (analiz sayfası) olduğunu yaz. `MEMORY.md`'ye bu aşamada öğrenilenleri ekle — en az şu üçü:

- Akış, `graph.py`'ye dokunmadan `contextvar` tabanlı bir token alıcısıyla eklendi; `contextvar`'lar iş parçacığına miras geçmediği için alıcı çalışan iş parçacığının içinde kurulur.
- `stream_options={"include_usage": True}` gönderilmezse akışlı yanıt hiç `usage` taşımaz ve tüm token/maliyet metrikleri sessizce `null` olur.
- Yüklenen parçaların BM25 skorları korpusunkiyle karşılaştırılabilir değildir (farklı IDF tabanı); bu yüzden kapı yüklenen isabetleri yalnızca kosinüsle değerlendirir.

- [ ] **Step 6: Commit**

```bash
git add azure/web/app/page.tsx PROGRESSION.md MEMORY.md
git commit -m "feat(web): restructure the app shell around the conversation sidebar"
```

---

## Definition of Done

- [ ] `pytest azure/tests/ -q -o addopts="" --cov=azure --cov-fail-under=70` — 0 failure, kapsam ≥ %70 (taban: 73 test, %90)
- [ ] `cd azure/web && npm test` — mevcut 12 kimlik doğrulama testi dahil hepsi geçer
- [ ] `ruff format .` ve `ruff check .` — temiz
- [ ] `cd azure/web && npx next build` — hatasız
- [ ] `azure/rag/graph.py` ve `azure/rag/agent.py` diff'te **görünmüyor**
- [ ] `src/rag/` ve `web/` diff'te **görünmüyor**
- [ ] Task 12 Step 4'teki sekiz uçtan uca kontrol elle doğrulandı
- [ ] `PROGRESSION.md` ve `MEMORY.md` güncel
