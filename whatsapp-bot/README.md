# PLAZA-I WhatsApp AI

Python/FastAPI bot with a protected staff dashboard, signed Meta webhooks,
SQLite message queue, and Tajik/Russian replies. Bot code is included in the repository `main` branch and is deployed as a separate Render service.

## Render configuration

- Runtime: Docker
- Dockerfile path: `whatsapp-bot/Dockerfile`
- Docker build context: `whatsapp-bot`
- One instance and one Uvicorn worker only
- Application reads Render's `PORT` and binds to `0.0.0.0`
- HTTP health endpoint: `/health`
- Staff dashboard: `/admin`
- Meta callback endpoint: `/webhook`

### Initial deployment

The initial free service runs with `DEMO_MODE=1`. This is an offline
simulation: it does not call OpenAI or send WhatsApp messages. Its local
database is temporary, so use only synthetic test conversations.

Set these values using Render Environment Variables, never in Git:

- `DEMO_MODE=1`
- `ADMIN_USERNAME=plazai`
- `ADMIN_PASSWORD`: a random secret of at least 20 characters
- `DATABASE_PATH=/app/data/plazai.sqlite3`

### Optional real-AI preview (without WhatsApp)

By default, the dashboard shows a **rule-based offline preview**, not a generative
AI. It cannot answer arbitrary questions. To test the actual OpenAI model in
the protected dashboard **without Meta/WhatsApp credentials**, first provision
an OpenAI API key with billing limits. Then set `DEMO_MODE=1`,
`AI_PREVIEW_MODE=1`, and `OPENAI_API_KEY` in Render Environment Variables.
The banner changes to `AI / САНҶИШ`. API calls may incur charges. Messages
are simulated and **are not sent to WhatsApp**.

Do not confuse ChatGPT subscriptions with separate OpenAI API billing.
Do not put API keys in source code, the demo chat, or GitHub.

### Expert knowledge & supervised learning

The assistant now has a static bilingual (Tajik/Russian) reference library covering
architecture, construction phases, estimation/BoQ, interiors and design styles,
3D visualisation, engineering coordination, author supervision, technical
supervision, permits, renovations and construction safety.

A manager can open `/admin` -> `Донишҳо` to:
1. Add a generic question and verified answer. It begins as **pending**.
2. Review and optionally edit pending answers, then approve or reject them.
3. Export manager-approved knowledge to JSON and restore it as pending entries.

By default, an answer typed by a **human manager** creates a pending candidate
provided it passes a conservative privacy check. Customer and AI messages never
become approved knowledge automatically. The bot uses only **approved** Q&A
for retrieval during OpenAI requests; the basic DEMO can retrieve approved
exact/keyword-matched answers. This is retrieval-based learning, not automatic
model-weight training or memorization of every customer message.

Only add non-confidential, company-authorized, generalized knowledge.
A filter rejects obvious contact numbers, email addresses, URLs and long numeric
identifiers, but a human reviewer **must still check for names, client details,
confidential plans, inaccuracies, and out-of-date local regulations**.

Set `SUGGEST_FROM_STAFF=0` to disable automatic pending candidates.
The knowledge endpoints require admin authentication; all mutations also require
the dashboard request header. User message payloads are not added to public
GitHub source files.

**Data durability:** The current Render Free service has an ephemeral filesystem.
Approved knowledge and suggestions in SQLite **can disappear after a restart or
redeployment**. Export a backup after each knowledge change. Before storing real
customer conversations or relying on continuous learning, provision an approved
durable database or persistent disk and a privacy/retention policy. Do not upgrade
to paid hosting without the owner's approval.

Professional caution: generic guidelines cannot provide a final local-code
compliance check, signed structural engineering calculation, precise final estimate,
or verified licensing status. These require current project documents, official
local standards and qualified personnel. No specific pricing, discounts or legal
claims should be invented.

### API usage and estimated running cost

The staff dashboard now displays a rolling 30-day estimate for OpenAI token
usage and categorized API errors. A protected endpoint at
`GET /api/admin/usage?days=30` supports reporting periods of 1, 7, 30 and 90
days. Results include the total number of API requests, successes/failures,
input/output tokens, cached input tokens and estimated USD cost.

The app uses the OpenAI Responses API's **reported** `usage` counters, including
`input_tokens_details.cached_tokens`, instead of assuming a fixed price for
each chat message. Estimates apply only to `gpt-5.4-mini` and its versioned
snapshots, at published text prices of **$0.75 input, $0.075 cached input,
$4.50 output per million tokens** (reviewed October 2026). For a different
model, the app marks an API success as *unpriced* instead of displaying a
possibly incorrect dollar amount.

No prompt text, contact number, API key or answer is stored in the metering
table. Event identifiers are SHA-256 hashed, and repeated events cannot be
billed twice in the local usage report. All metrics require administrator
authentication and the response is `Cache-Control: no-store`.

**This is an estimate, not an OpenAI invoice, quota balance, or payment
service.** Actual OpenAI usage and billing details must be viewed in OpenAI
Platform. It does not cover Meta WhatsApp messaging fees, Render server costs,
taxes or provider-side charges not included in the reported token usage.

The current free Render service has ephemeral SQLite storage: the usage report
can be lost after redeployment or restart. For a complete historical record,
a separately approved, durable database is required.

The bot does not initiate payments, adjust credit limits, or change billing
configuration. OpenAI API returns HTTP 429 (quota or rate limit) until the
account-level cause is resolved.

### OpenAI + Meta preflight (no credentials revealed)

The protected staff dashboard has **Омодагии пайвасти WhatsApp ва AI**.
Its endpoint `GET /api/admin/integration-status` reports only boolean
presence/absence of required environment variable names. It does **not**
return credentials, card data, Meta tokens, actual API billing status, or
proof that the business number is registered. Authentication is required;
responses are `Cache-Control: no-store`.

**Fail closed:** `POST /webhook` rejects ALL real WhatsApp messages when
`DEMO_MODE=1`, even if credentials were entered early. This prevents
unintended collection of real customer messages on temporary Render Free
storage. `GET /webhook` can still verify a matching `META_VERIFY_TOKEN`.
Do not flip `DEMO_MODE=0` until OpenAI billing, Meta authorization,
persistent storage, and production readiness have been verified.

Recommended safe onboarding order:

1. An authorized adult account owner sets up OpenAI API billing in OpenAI
   Platform (separate from ChatGPT) and verifies that the quota 429 error
   is resolved. Never paste payment details or API keys into a chat.
2. The authorized Meta Business Portfolio admin opens the WhatsApp product
   in their Meta developer app, reviews business eligibility, obtains the
   WhatsApp Business Account and Phone Number IDs, verifies control of the
   phone number and configures a system-user access token with the minimum
   `whatsapp_business_messaging` permissions needed.
3. If the number is currently used in the **WhatsApp Business phone app**,
   verify the supported **Coexistence** onboarding method BEFORE enrolling
   the number in Cloud API. Do not delete the WhatsApp Business app or
   disconnect its number in the hope that it will work automatically.
   Phone eligibility depends on Meta and the selected onboarding path.
4. Configure Meta webhooks: callback
   `https://plaza-i-whatsapp-bot.onrender.com/webhook`, and verify
   token matching `META_VERIFY_TOKEN` in Render. Subscribe to messages.
   Token must be a unique random secret; never publish it in GitHub.
5. Set Render variables `META_ACCESS_TOKEN`, `META_APP_SECRET`,
   `META_VERIFY_TOKEN`, `META_PHONE_NUMBER_ID`; keep `DEMO_MODE=1`
   while staging. Use the dashboard to confirm the names are configured.
6. Provision persistent storage, reliable always-on hosting, and appropriate
   consent/retention protections before enabling real customer intake.
   Then `DEMO_MODE=0`, `AI_PREVIEW_MODE=0`, deploy, verify inbound
   signed webhooks and Meta API outbound delivery with an authorized
   test recipient. This step should not be undertaken automatically
   before the business owner authorizes the live rollout.

Render Free sleeps after 15 minutes idle and its local SQLite data is
lost on redeploy/restart/spin-down. Do not use it for live business chats.
Production hosting/database plans require separately approved charges.

### Live operation

Before setting `DEMO_MODE=0`:

1. Provision a paid, always-running web service with a persistent disk mounted
   at `/app/data`. The free service is unsuitable for durable customer chats.
   Approve the hosting cost before enabling paid resources.
2. Configure `OPENAI_API_KEY` and an available `OPENAI_MODEL` in Render.
3. Configure `META_ACCESS_TOKEN`, `META_APP_SECRET`, `META_PHONE_NUMBER_ID`,
   `META_GRAPH_VERSION`, and a strong random `META_VERIFY_TOKEN` in Render.
4. In Meta, configure the deployed `/webhook` URL, use the same verification
   token, and subscribe to the `messages` field.
5. Verify the eligible official onboarding route for the intended business
   number. Do not delete the existing WhatsApp Business account from the phone.
6. Set `DEMO_MODE=0`, redeploy, verify `/health`, then test an inbound message
   and its reply with an authorized test recipient.

Changing environment variables does not itself prove that WhatsApp is connected.
Connection is complete only after a successful signed inbound webhook and a
confirmed outbound WhatsApp response.

The bot supports text only. Price questions and requests for a manager switch
the conversation to human handling. Staff can manage each conversation in
`/admin`. Free-text replies remain subject to Meta's customer-service window.

## Local verification

Use Python 3.12 or later:

```bash
cd whatsapp-bot
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest -q
```

The production service has no public demo endpoint: the simulation and staff
APIs require the configured administrator password. Never commit API keys,
administrator credentials, customer conversations, or SQLite database files.
