# PLAZA-I WhatsApp AI

Python/FastAPI bot with a protected staff dashboard, signed Meta webhooks,
SQLite message queue, and Tajik/Russian replies. Source is deployed separately
from the PLAZA-I website on branch `codex/plaza-i-whatsapp-bot`.

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
