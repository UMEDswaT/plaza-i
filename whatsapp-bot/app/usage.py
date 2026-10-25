"""Privacy-minimal OpenAI API usage ledger for PLAZA-I.

Only SHA-256 event digests, token counts, UTC times and status categories are
stored. No customer text, phone numbers, API credentials or response bodies.

Prices are a snapshot (USD per million text tokens): OpenAI GPT-5.4 Mini
input 0.75, cached input 0.075, output 4.50. Estimates, not actual invoices.
"""
import hashlib
import os
import sqlite3
import time
from contextlib import contextmanager

# USD per one million tokens. No unverified pricing for other models.
MODEL_PRICING = {
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
}


def estimate_usd(model: str, input_tokens: int, output_tokens: int,
                 cached_input_tokens: int = 0) -> float | None:
    name = str(model or "").lower()
    if name.startswith("gpt-5.4-mini-"):
        name = "gpt-5.4-mini"
    rates = MODEL_PRICING.get(name)
    if rates is None:
        return None
    if any(type(v) is not int or v < 0 for v in
           (input_tokens, output_tokens, cached_input_tokens)):
        raise ValueError("Token counts must be nonnegative integers")
    if cached_input_tokens > input_tokens:
        raise ValueError("Cached input exceeds total input")
    input_rate, cached_rate, output_rate = rates
    return ((input_tokens - cached_input_tokens) * input_rate
            + cached_input_tokens * cached_rate
            + output_tokens * output_rate) / 1_000_000


class UsageLedger:
    """Idempotent SQLite usage accounting, local to one Render instance."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS api_usage (
                event_hash TEXT PRIMARY KEY,
                created REAL NOT NULL,
                status TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                cached_input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                estimated_usd REAL,
                CHECK (input_tokens >= 0),
                CHECK (cached_input_tokens >= 0),
                CHECK (output_tokens >= 0)
            );
            CREATE INDEX IF NOT EXISTS api_usage_created
                ON api_usage(created);
            """)

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def hash_event(event_id: str) -> str:
        return hashlib.sha256(event_id.encode("utf-8")).hexdigest()

    def record_success(self, event_id: str, model: str, details: dict):
        if not isinstance(details, dict):
            return False
        values = (
            details.get("input_tokens", 0),
            details.get("output_tokens", 0),
            details.get("input_tokens_details", {}).get("cached_tokens", 0)
        )
        if any(type(x) is not int or x < 0 for x in values):
            return False
        inputs, outputs, cached = values
        if cached > inputs:
            return False
        cost = estimate_usd(model, inputs, outputs, cached)
        with self.db() as db:
            row = db.execute(
                "INSERT OR IGNORE INTO api_usage"
                "(event_hash,created,status,model,input_tokens,cached_input_tokens,"
                "output_tokens,estimated_usd) VALUES(?,?,?,?,?,?,?,?)",
                (self.hash_event(event_id), time.time(), "success",
                 model[:100], inputs, cached, outputs, cost)
            )
            return row.rowcount > 0

    def record_error(self, event_id: str, model: str, category: str):
        if category not in ("quota", "limit", "auth", "request", "other"):
            category = "other"
        with self.db() as db:
            row = db.execute(
                "INSERT OR IGNORE INTO api_usage "
                "(event_hash,created,status,model) VALUES(?,?,?,?)",
                (self.hash_event(event_id), time.time(), category, model[:100])
            )
            return row.rowcount > 0

    def summary(self, days: int = 30) -> dict:
        if type(days) is not int or days not in (1, 7, 30, 90):
            raise ValueError("Unsupported reporting interval")
        with self.db() as db:
            rows = db.execute("""
                SELECT status, model, COUNT(*) AS events,
                       SUM(input_tokens) AS input_tokens,
                       SUM(cached_input_tokens) AS cached_input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(COALESCE(estimated_usd, 0)) AS estimated_usd,
                       SUM(CASE WHEN status='success' AND
                                    estimated_usd IS NULL THEN 1 ELSE 0 END) AS unpriced
                FROM api_usage WHERE created>=?
                GROUP BY status,model
                ORDER BY events DESC
            """, (time.time() - days*86400,)).fetchall()
        totals = {
            "requests": 0, "successful": 0, "failed": 0,
            "input_tokens": 0, "cached_input_tokens": 0,
            "output_tokens": 0, "estimated_usd": 0.0,
            "unpriced_successes": 0, "errors": {}
        }
        for row in rows:
            qty = row["events"]
            totals["requests"] += qty
            if row["status"] == "success":
                totals["successful"] += qty
            else:
                totals["failed"] += qty
                totals["errors"][row["status"]] = (
                    totals["errors"].get(row["status"], 0) + qty)
            for name in ("input_tokens", "cached_input_tokens", "output_tokens"):
                totals[name] += row[name] or 0
            totals["estimated_usd"] += row["estimated_usd"] or 0
            totals["unpriced_successes"] += row["unpriced"] or 0
        totals["estimated_usd"] = round(totals["estimated_usd"], 6)
        return {"days": days, "totals": totals,
                "pricing_note": ("Estimate from reported API text-token usage. "
                                 "Not OpenAI billing; excludes WhatsApp/hosting. "
                                 "Ephemeral storage may reset on Render Free."),
                "pricing_model": "gpt-5.4-mini"}
