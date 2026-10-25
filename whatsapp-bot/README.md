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
