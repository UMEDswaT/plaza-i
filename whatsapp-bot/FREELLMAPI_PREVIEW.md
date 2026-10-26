# FreeLLMAPI preview (not production)

FreeLLMAPI is a self-hosted single-user router for personal experimentation, not a hosted free commercial API. Its upstream free tiers have variable quotas and terms.

On a local development copy of PLAZA-I with a locally running router, set private environment variables:

```dotenv
DEMO_MODE=1
AI_PREVIEW_MODE=1
AI_PROVIDER=freellmapi
FREELLMAPI_BASE_URL=http://127.0.0.1:3001/v1
FREELLMAPI_API_KEY=your-router-unified-key
FREELLMAPI_MODEL=auto
```

Never commit or share credentials. localhost on Render is **not your phone/computer**, so this configuration alone cannot make the existing Render service use the router. Never expose a local single-user router publicly. This preview is disabled in live mode; real WhatsApp customer messages still require Meta authorization, compliant production inference, durable hosting and storage.

OpenAI remains the default provider, and there is no automatic paid fallback. FreeLLMAPI token usage is marked unpriced, not assumed to cost zero.
