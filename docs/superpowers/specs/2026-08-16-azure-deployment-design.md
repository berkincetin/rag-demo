# Azure Deployment Design — Part 1 RAG Agent

**Date:** 2026-08-16
**Status:** Approved for planning
**Scope:** Deploy the Part 1 RAG agent to Azure as a two-tier, authenticated,
cloud-only application. Part 2 (the analysis notebook) is out of scope.

---

## 1. Context

The RAG agent currently runs locally: Ollama for chat, `sentence-transformers`
(`intfloat/multilingual-e5-base`) for embeddings, a Gradio UI and a Next.js UI
in front of a FastAPI backend, orchestrated by `docker compose`. The Python
image is ~7.4 GB, dominated by torch and the pre-baked embedding model.

This design adds an Azure deployment target. It does **not** modify the local
setup.

### 1.1 Verified Azure inventory

Measured with `az` on 2026-08-16, not assumed:

| Resource | Value | Action |
|---|---|---|
| Subscription | `Azure subscription 1` (`67f6f558-…`) | reuse |
| Resource group | `foundry-lab-rg` (eastus) | reuse |
| Azure OpenAI | `foundry-lab-hbc26` (kind `AIServices`) | reuse |
| OpenAI endpoint | `https://foundry-lab-hbc26.openai.azure.com/` | reuse |
| Chat deployment | `gpt-4.1-mini`, ver `2025-04-14`, GlobalStandard, capacity 100 | reuse, untouched |
| Embedding deployment | **none exists** | **create** |
| `text-embedding-3-small` | available on the resource, version `1` | deploy |
| Container registry | `cad8870592d9acr` (Basic, 10 GB) | reuse |
| Container Apps env | `azure-rag-env` | reuse |
| `azure-rag`, `azure-rag-web` | **a different project**, currently running | **do not touch** |

The existing `azure-rag*` apps belong to an unrelated project. Their names
collide with the obvious names for this one, so this deployment uses the
`nobel-rag-*` prefix in both ACR and Container Apps.

---

## 2. Goals and non-goals

### Goals

1. Run Part 1 on Azure with **no local models** — Azure OpenAI for both chat
   and embeddings.
2. Require **authentication** before any application function is reachable.
3. Keep the **backend unreachable from the internet**; only the web tier is
   public.
4. Leave `src/rag/`, `gradio_app.py`, and `docker-compose.yml` **byte-identical**
   so the local offline path and its 329 tests keep working.
5. Keep idle cost near zero (demo deployment).

### Non-goals

- Multi-user accounts, user management, or an identity provider.
- Running Ollama or any local model on Azure.
- Deploying the Part 2 notebook.
- Production-grade horizontal scale (see §8 limitation on rate limiting).
- Changing the local development experience in any way.

---

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | `azure/` is an **independent copy**, not a refactor of `src/rag/` | The user chose absolute isolation. The local path cannot regress from Azure work; its test suite keeps guarding it. Accepted cost: duplicated retrieval logic (~400 lines) must be fixed in two places. |
| D2 | Chat model: `gpt-4.1-mini` | Already deployed with capacity 100. Supports tool calling, which the agent's 3 tools require. |
| D3 | Embeddings: `text-embedding-3-small` | Cloud-only requirement. Removes torch + the 1.1 GB model: image ~7.4 GB → ~1.5 GB. Keeps ACR Basic (10 GB) viable alongside the existing project's images. |
| D4 | **Drop the E5 `passage:` / `query:` prefixes** | They are E5 training artifacts. Passed to `text-embedding-3-small` they become literal content and silently degrade retrieval. Must be removed, not ported. |
| D5 | **Recalibrate `MIN_COSINE` / `MIN_BM25`** | The current values (0.80 / 5.0) were measured against e5-base. A different embedding model has a different cosine distribution, so they are invalid by construction. |
| D6 | Backend uses **internal ingress** | The user requires the backend not be exposed. Removes the public attack surface entirely. |
| D7 | Front-end proxies to the backend (BFF) | Consequence of D6: the browser cannot reach an internal app, and the current client calls the API directly from the browser. |
| D8 | Single shared username + password | Right weight for a case demo. No identity provider setup, no tenant membership needed for an external evaluator. |
| D9 | **Remove the API-key entry UI** | With a single server-held provider, key-entry endpoints are pure attack surface. Azure OpenAI credentials live only in Container Apps secrets. |
| D10 | Metrics visible; evaluation and metrics-deletion removed | Evaluation runs 13 cases × N models per call — a cost-amplification endpoint. Metrics display carries the showcase value without the risk. |
| D11 | Ingest runs locally; the index ships inside the image | ~276 chunks is a fraction of a cent to embed once, and it keeps cold start fast. No persistent volume needed. |

---

## 4. Architecture

```
Internet ──HTTPS──▶ nobel-rag-web            external ingress, :3000
                    Next.js
                    ├─ /login
                    ├─ middleware.ts          (auth guard)
                    └─ /api/proxy/[...path]   (server-side BFF)
                              │
                              │  internal network only
                              ▼
                    nobel-rag-api            INTERNAL ingress, :8000
                    FastAPI · Chroma · BM25
                              │
                              ▼
                    foundry-lab-hbc26        Azure OpenAI
                    gpt-4.1-mini · text-embedding-3-small
```

Because every browser call is same-origin against the web tier, **CORS becomes
irrelevant**; the `CORS_ORIGINS` handling in `src/rag/api.py` is dropped in the
Azure build rather than widened.

### 4.1 Repository layout

```
azure/
  rag/
    config.py          Azure settings (endpoint, deployments, api-version)
    embedder.py        AzureOpenAIEmbedder — text-embedding-3-small
    llm_client.py      AzureOpenAIClient — gpt-4.1-mini, tool calling
    index.py           Chroma + BM25          (copy; E5 prefixes removed)
    retriever.py       hybrid + RRF + gate    (copy; E5 prefixes removed)
    agent.py           LangGraph agent loop   (copy)
    api.py             FastAPI                (copy; see §4.2)
    metrics.py         SQLite metrics store   (copy; metrics stay visible)
    serialize.py       JSON payload shapes    (copy; key/eval shapes dropped)
    catalog.py         single Azure model     (copy, reduced)
    pricing.py         gpt-4.1-mini pricing   (copy; see §4.3)
    ui_state.py        session state          (copy; key handling dropped)
    memory.py          chat memory            (copy)
    normalize.py chunker.py loaders/ tools.py prompts.py models.py
                       (copies, unchanged logic)
  web/                 Next.js (copy) + auth + proxy
    middleware.ts
    app/login/page.tsx
    app/api/auth/login/route.ts
    app/api/auth/logout/route.ts
    app/api/proxy/[...path]/route.ts
    lib/auth.ts        JWT sign/verify, bcrypt compare
    lib/api.ts         (copy; BASE becomes "/api/proxy")
  Dockerfile           slim: no torch, no sentence-transformers
  requirements.txt     cloud-only dependency set
  scripts/
    provision.sh       idempotent az CLI provisioning
    deploy.sh          build → ACR push → containerapp update
    ingest.py          builds the index that gets baked into the image
    calibrate.py       measures thresholds (see §6)
  tests/               pytest for the Azure modules
```

Modules dropped from the Azure copy: `ollama_admin.py`, `resources.py`,
`credentials.py`, `evaluation.py` — all meaningless or unwanted in a
cloud-only, single-provider, authenticated container.

### 4.2 Backend endpoints in the Azure build

| Endpoint | Status |
|---|---|
| `POST /api/ask` | kept |
| `POST /api/chat/clear` | kept |
| `GET /api/models` | kept (returns the single Azure model) |
| `GET /api/metrics` | kept |
| `GET /api/health` | kept |
| `POST /api/keys`, `GET /api/keys` | **removed** (D9) |
| `GET/POST /api/ollama*` | **removed** |
| `POST /api/evaluation/*` | **removed** (D10) |
| `DELETE /api/metrics` | **removed** (D10) |

### 4.3 Pricing data

`config/model_prices.json` carries no entry for `gpt-4.1-mini`, and its own
header warns against inventing prices ("Uydurma fiyat girmeyin"). Azure OpenAI
pricing also differs from the OpenAI API's and varies by region and tier.

Therefore the entry is added with `null` input/output prices unless verified
Azure pricing is supplied. The UI already handles this: it displays
"price not entered" and excludes unpriced runs from cost charts, exactly as it
does today for `gpt-4o-mini` and `gemini-3.5-flash`. Token counts are still
recorded and shown — only the money figure is withheld.

---

## 5. Authentication and security

### 5.1 Login flow

```
POST /api/auth/login  { username, password }
  ├─ constant-time username comparison
  ├─ bcrypt.compare(password, APP_PASSWORD_HASH)
  ├─ failure → generic error, no field-level hint, attempt throttle
  └─ success → JWT (HS256, 8h) in a cookie:
                httpOnly · Secure · SameSite=Lax · Path=/
```

The password exists **only as a bcrypt hash**, supplied as a Container Apps
secret. Plaintext appears in no file, image layer, or environment variable.

`middleware.ts` guards all routes and all proxy paths. Page requests without a
valid session redirect to `/login`; proxy requests get a bare `401`.

### 5.2 Session integrity — the hijack fix

Today `X-Session-Id` is minted by the browser (`web/lib/api.ts`), so any caller
can address any session and read its chat history and provider state. In the
Azure build:

```
sessionId = JWT claim "sid"        random UUID, minted server-side at login
```

The proxy **overwrites** any client-supplied `X-Session-Id` rather than
forwarding it. The id is unforgeable without the signing secret.

### 5.3 Defense in depth

| Layer | Control |
|---|---|
| Network | Backend internal ingress — no public FQDN |
| Transport | Container Apps enforces HTTPS; `Secure` cookie |
| Tier-to-tier | Backend requires `X-Internal-Token` equal to a shared secret; a compromised sibling container still cannot call it |
| Identity | bcrypt hash + HS256 JWT, 8h expiry |
| Session | Server-derived `sid`; client header ignored |
| Rate limit | Per-session throttle on `/api/ask`; per-IP throttle on login |
| Surface | Key, Ollama, evaluation and metrics-deletion endpoints absent |
| Secrets | Container Apps secrets only; never in the image or git |
| Headers | CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS |

### 5.4 Secrets

| Secret | Holder | Purpose |
|---|---|---|
| `azure-openai-key` | api | Azure OpenAI authentication |
| `app-password-hash` | web | bcrypt hash of the login password |
| `session-secret` | web | JWT signing key |
| `internal-token` | web + api | Tier-to-tier authentication |

---

## 6. Retrieval recalibration

This is the design's main correctness risk and is treated as a first-class
step, not a footnote.

`MIN_COSINE=0.80` and `MIN_BM25=5.0` were calibrated in Part 1 Task 9 against
e5-base. `text-embedding-3-small` produces a different similarity
distribution, so reusing those numbers would either refuse valid questions or
admit off-topic ones. The "I don't know" gate is a graded case requirement, so
this must be measured.

**Method** (mirrors the original Task 9 procedure):

1. Build the Azure index over the real 6 documents.
2. Run the 7 known-good probe queries and 5 off-topic queries.
3. Record the actual cosine and BM25 distributions for both groups.
4. Choose thresholds that separate them, with the same AND-gate semantics.
5. Confirm against the 13-case evaluation set, run locally against the Azure
   backend before deployment.

BM25 is independent of embeddings, so `MIN_BM25` is expected to hold — but it
is re-measured rather than assumed.

**If the two groups do not separate cleanly, that is reported as a finding**,
not tuned until the numbers look agreeable.

---

## 7. Testing strategy

TDD per `CLAUDE.md` §3: a failing test precedes every implementation step.
Coverage gate stays at ≥70%. LLM output text is never asserted on.

**Security tests (written first):**

- Correct password accepted; wrong password rejected
- Plaintext password never appears in any response or log
- Tampered, expired, and unsigned JWTs rejected
- Unauthenticated proxy request → 401 **and the backend is never called**
- Client-supplied `X-Session-Id` ignored; cookie `sid` substituted
- Backend rejects a request missing `X-Internal-Token`
- Removed endpoints return 404

**Embedder and LLM client:** unit tests against a mocked Azure client —
request shape, tool-call parsing, token-usage mapping, error handling.

**Index and retriever:** integration tests over the real 6 documents,
asserting the same facts the local suite does, including that `1.500 TL/ay`
is retrievable from the DOCX table.

---

## 8. Known limitations

Stated explicitly rather than discovered later:

1. **Rate limiting is in-memory, therefore per-replica.** Effective for demo
   traffic with scale-to-zero; approximate under multi-replica scale. A shared
   store would be required for a production guarantee.
2. **Cold start pays two container starts in sequence** (`minReplicas=0` on
   both tiers): roughly 15–40s on the first request, fast thereafter. Setting
   `minReplicas=1` on the web tier removes most of it at a small monthly cost.
3. **`azure/` duplicates retrieval logic.** A bug fixed in one path must be
   fixed in the other. This is the accepted cost of D1's isolation guarantee.
4. **Single shared credential** — no per-user attribution or revocation.

---

## 9. Sequencing

1. Provision `text-embedding-3-small`; verify quota by deploying it.
2. Build `azure/rag/` with TDD (embedder → LLM client → index → retriever →
   agent → api).
3. Ingest locally and **recalibrate thresholds** (§6).
4. Build `azure/web/` auth and proxy with TDD.
5. Verify the whole stack locally via an Azure-targeted compose file.
6. Push both images to ACR as `nobel-rag-api` / `nobel-rag-web`.
7. Create both container apps with correct ingress and secrets.
8. Verify end to end against the live URL: login required, backend
   unreachable from the internet, a grounded answer with citations, and a
   correct refusal on an off-topic question.

---

## 10. Definition of Done

- [ ] `text-embedding-3-small` deployed on `foundry-lab-hbc26`
- [ ] `src/rag/`, `gradio_app.py`, `docker-compose.yml` unchanged; local suite green
- [ ] Azure image contains no torch and no `sentence-transformers`
- [ ] Thresholds recalibrated from measured data, values recorded with evidence
- [ ] All §7 security tests pass
- [ ] Backend has no public FQDN; direct access attempt fails
- [ ] Application unreachable without login
- [ ] Live URL answers a grounded question with citations
- [ ] Live URL refuses an off-topic question
- [ ] Existing `azure-rag` / `azure-rag-web` still running, untouched
- [ ] Quality gate green: `ruff format`, `ruff check`, `pytest --cov --cov-fail-under=70`
