# Task 14: Deploy and Verify

**Goal:** Push both images, create both container apps with correct ingress and
secrets, and verify the live deployment end to end.

**Files:**
- Create: `azure/scripts/provision.sh`
- Create: `azure/scripts/deploy.sh`
- Create: `azure/README.md`
- Modify: `PROGRESSION.md`, `MEMORY.md`

**Interfaces:**
- Consumes: `nobel-rag-api:local`, `nobel-rag-web:local` (Tasks 11, 13)
- Produces: a live HTTPS URL

---

## ⚠️ Guard rails

- **Never touch `azure-rag` or `azure-rag-web`.** Different project, currently
  running. Every command below names `nobel-rag-*`.
- **Never pass secrets on a command line that gets logged.** Use
  `--secrets name=value` at creation and reference them with `secretref:`.
- Confirm the other project is still running at the end.

- [ ] **Step 1: Record the pre-state**

```bash
az containerapp list -g foundry-lab-rg --query "[].name" -o tsv | sort > /tmp/apps-before.txt
cat /tmp/apps-before.txt
```

Expected: `azure-rag` and `azure-rag-web`.

- [ ] **Step 2: Write the provisioning script**

Create `azure/scripts/provision.sh`:

```bash
#!/usr/bin/env bash
# Idempotent provisioning for the Nobel RAG deployment.
#
# Creates only what is missing. Never touches azure-rag / azure-rag-web —
# those belong to a different project running in the same resource group.
set -euo pipefail

RG=foundry-lab-rg
ENV=azure-rag-env
ACR=cad8870592d9acr
OPENAI=foundry-lab-hbc26
API_APP=nobel-rag-api
WEB_APP=nobel-rag-web

: "${APP_USERNAME:?set APP_USERNAME}"
: "${APP_PASSWORD_HASH:?set APP_PASSWORD_HASH}"
: "${SESSION_SECRET:?set SESSION_SECRET (32+ chars)}"
: "${MIN_COSINE:?set MIN_COSINE from Task 8 calibration}"
: "${MIN_BM25:?set MIN_BM25 from Task 8 calibration}"

INTERNAL_TOKEN="${INTERNAL_TOKEN:-$(openssl rand -hex 32)}"
OPENAI_KEY=$(az cognitiveservices account keys list -n "$OPENAI" -g "$RG" --query key1 -o tsv)
ACR_SERVER=$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)

echo "==> backend: $API_APP (internal ingress)"
if az containerapp show -n "$API_APP" -g "$RG" >/dev/null 2>&1; then
  echo "    already exists — skipping creation"
else
  az containerapp create \
    -n "$API_APP" -g "$RG" --environment "$ENV" \
    --image "$ACR_SERVER/$API_APP:latest" \
    --registry-server "$ACR_SERVER" \
    --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --target-port 8000 --ingress internal \
    --min-replicas 0 --max-replicas 3 \
    --cpu 1.0 --memory 2Gi \
    --secrets \
      azure-openai-key="$OPENAI_KEY" \
      internal-token="$INTERNAL_TOKEN" \
    --env-vars \
      AZURE_OPENAI_API_KEY=secretref:azure-openai-key \
      INTERNAL_TOKEN=secretref:internal-token \
      AZURE_OPENAI_ENDPOINT="https://$OPENAI.openai.azure.com/" \
      AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4.1-mini \
      AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small \
      MIN_COSINE="$MIN_COSINE" \
      MIN_BM25="$MIN_BM25" \
      STORAGE_DIR=/app/azure/storage \
      DATA_DIR=/app/data
fi

BACKEND_FQDN=$(az containerapp show -n "$API_APP" -g "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)
echo "    internal FQDN: $BACKEND_FQDN"

echo "==> frontend: $WEB_APP (external ingress)"
if az containerapp show -n "$WEB_APP" -g "$RG" >/dev/null 2>&1; then
  echo "    already exists — skipping creation"
else
  az containerapp create \
    -n "$WEB_APP" -g "$RG" --environment "$ENV" \
    --image "$ACR_SERVER/$WEB_APP:latest" \
    --registry-server "$ACR_SERVER" \
    --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
    --target-port 3000 --ingress external \
    --min-replicas 0 --max-replicas 3 \
    --cpu 0.5 --memory 1Gi \
    --secrets \
      app-password-hash="$APP_PASSWORD_HASH" \
      session-secret="$SESSION_SECRET" \
      internal-token="$INTERNAL_TOKEN" \
    --env-vars \
      APP_USERNAME="$APP_USERNAME" \
      APP_PASSWORD_HASH=secretref:app-password-hash \
      SESSION_SECRET=secretref:session-secret \
      INTERNAL_TOKEN=secretref:internal-token \
      BACKEND_URL="https://$BACKEND_FQDN"
fi

echo
echo "==> live URL:"
az containerapp show -n "$WEB_APP" -g "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv
```

- [ ] **Step 3: Write the deploy script**

Create `azure/scripts/deploy.sh`:

```bash
#!/usr/bin/env bash
# Build, push and roll out both tiers.
set -euo pipefail

RG=foundry-lab-rg
ACR=cad8870592d9acr
ACR_SERVER=$(az acr show -n "$ACR" -g "$RG" --query loginServer -o tsv)
TAG="${1:-latest}"

az acr login -n "$ACR"

echo "==> building backend"
docker build -f azure/Dockerfile -t "$ACR_SERVER/nobel-rag-api:$TAG" .
docker push "$ACR_SERVER/nobel-rag-api:$TAG"

echo "==> building frontend"
docker build -t "$ACR_SERVER/nobel-rag-web:$TAG" azure/web
docker push "$ACR_SERVER/nobel-rag-web:$TAG"

echo "==> rolling out"
az containerapp update -n nobel-rag-api -g "$RG" --image "$ACR_SERVER/nobel-rag-api:$TAG"
az containerapp update -n nobel-rag-web -g "$RG" --image "$ACR_SERVER/nobel-rag-web:$TAG"

echo "==> live URL:"
az containerapp show -n nobel-rag-web -g "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv
```

- [ ] **Step 4: Push the images**

The apps do not exist yet, so push before provisioning:

```bash
az acr login -n cad8870592d9acr
docker tag nobel-rag-api:local cad8870592d9acr.azurecr.io/nobel-rag-api:latest
docker tag nobel-rag-web:local cad8870592d9acr.azurecr.io/nobel-rag-web:latest
docker push cad8870592d9acr.azurecr.io/nobel-rag-api:latest
docker push cad8870592d9acr.azurecr.io/nobel-rag-web:latest
```

- [ ] **Step 5: Check the registry has room**

```bash
az acr show-usage -n cad8870592d9acr -o table
```

ACR Basic allows 10 GB. If the two new repositories would exceed it, report
the numbers rather than deleting anything — the other project's images live
here too.

- [ ] **Step 6: Provision**

```bash
export APP_USERNAME=demo
export APP_PASSWORD_HASH='<hash from Task 12>'
export SESSION_SECRET="$(openssl rand -hex 32)"
export MIN_COSINE='<measured in Task 8>'
export MIN_BM25='<measured in Task 8>'

bash azure/scripts/provision.sh
```

Record the printed live URL.

- [ ] **Step 7: Verify the backend is not publicly reachable**

```bash
az containerapp show -n nobel-rag-api -g foundry-lab-rg \
  --query "{external:properties.configuration.ingress.external,fqdn:properties.configuration.ingress.fqdn}" -o json
```

Expected: `"external": false` and an FQDN containing `.internal.`.

Then prove it from outside:

```bash
curl -s -o /dev/null -w "direct backend: %{http_code}\n" --max-time 15 \
  "https://$(az containerapp show -n nobel-rag-api -g foundry-lab-rg --query properties.configuration.ingress.fqdn -o tsv)/api/health" \
  || echo "unreachable from the internet — correct"
```

Expected: a DNS/connection failure. A `200` here means the ingress is wrong —
stop and fix it.

- [ ] **Step 8: Verify login is required**

```bash
URL=$(az containerapp show -n nobel-rag-web -g foundry-lab-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

curl -s -o /dev/null -w "anon root: %{http_code} → %{redirect_url}\n" "https://$URL/"
curl -s -o /dev/null -w "anon proxy: %{http_code}\n" -X POST "https://$URL/api/proxy/api/ask" \
  -H "Content-Type: application/json" -d '{"question":"test"}'
curl -s -o /dev/null -w "wrong password: %{http_code}\n" -X POST "https://$URL/api/auth/login" \
  -H "Content-Type: application/json" -d '{"username":"demo","password":"yanlis"}'
```

Expected: a redirect to `/login`, `401` from the proxy, `401` for the wrong
password.

- [ ] **Step 9: Verify a grounded answer and a refusal**

```bash
curl -s -c /tmp/jar -X POST "https://$URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"demo\",\"password\":\"<parola>\"}"

echo "--- grounded ---"
curl -s -b /tmp/jar -X POST "https://$URL/api/proxy/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Araç yakıt limiti ne kadar?"}'

echo "--- off-topic ---"
curl -s -b /tmp/jar -X POST "https://$URL/api/proxy/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Bugün hava nasıl?"}'
```

Expected: the first answer contains `1.500 TL/ay` with a non-empty
`citations`; the second refuses with `citations: []`.

Paste both responses into the commit message — this is the DoD evidence.

- [ ] **Step 10: Verify in a browser**

Open `https://$URL`, log in, ask a question. Confirm the answer, the sources
panel and the tool trace render, and that no API-key or Ollama panel is
present. Log out and confirm the redirect back to `/login`.

- [ ] **Step 11: Confirm the other project is untouched**

```bash
az containerapp list -g foundry-lab-rg --query "[].name" -o tsv | sort > /tmp/apps-after.txt
diff /tmp/apps-before.txt /tmp/apps-after.txt

az containerapp show -n azure-rag -g foundry-lab-rg \
  --query "{image:properties.template.containers[0].image,revision:properties.latestRevisionName}" -o json
az containerapp show -n azure-rag-web -g foundry-lab-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv
```

Expected: the diff shows only the two added `nobel-rag-*` lines, and
`azure-rag`'s image is still `cad8870592d9acr.azurecr.io/azure-rag:latest`.

Then confirm it still serves:

```bash
curl -s -o /dev/null -w "other project: %{http_code}\n" \
  "https://azure-rag-web.proudgrass-895fc7d5.eastus.azurecontainerapps.io/"
```

- [ ] **Step 12: Write `azure/README.md`**

Cover: the architecture diagram, the deployment commands, the environment
variables and their sources, the measured thresholds with a pointer to
`CALIBRATION.md`, the security model, and the limitations from spec §8
(per-replica rate limiting, cold start, duplicated retrieval logic, single
shared credential).

**Do not put the password, the hash, or any key in this file.**

- [ ] **Step 13: Update the state files**

In `PROGRESSION.md`, add a row to the phase-closure table with the date, the
tasks, the test result and the live URL. In `MEMORY.md`, record what cost time
— at minimum the Edge/Node runtime split for `jose` vs `bcryptjs`, the E5
prefix removal, and the calibration outcome.

Both files are written in Turkish (CLAUDE.md §6).

- [ ] **Step 14: Final verification**

```bash
git status --short src/ tests/ web/ gradio_app.py docker-compose.yml Dockerfile app.py
```

Expected: no output — the local path survived the whole plan untouched.

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 15: Commit and push**

```bash
git add azure/ PROGRESSION.md MEMORY.md docs/
git commit -m "feat(azure): deploy two-tier authenticated RAG app to Container Apps"
git push origin main
```

- [ ] **Step 16: Report**

State, with evidence:

- The live URL
- That the backend is unreachable from the internet (Step 7 output)
- That login is enforced (Step 8 output)
- The grounded answer and the refusal (Step 9 output)
- The measured thresholds
- That the other project is untouched (Step 11 output)
- Any DoD line that was **not** met, and why
