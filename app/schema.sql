CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT NOT NULL DEFAULT '',
    billing_email TEXT NOT NULL DEFAULT '',
    handoff_phone TEXT NOT NULL DEFAULT '',
    timezone_default TEXT NOT NULL DEFAULT 'America/New_York',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    offer_summary TEXT NOT NULL DEFAULT '',
    goal TEXT NOT NULL DEFAULT 'appointment_booking',
    approved_claims_json TEXT NOT NULL DEFAULT '[]',
    disallowed_claims_json TEXT NOT NULL DEFAULT '[]',
    ai_disclosure_mode TEXT NOT NULL DEFAULT 'conservative',
    recording_mode TEXT NOT NULL DEFAULT 'transcript_only',
    calling_window_start TEXT NOT NULL DEFAULT '09:00',
    calling_window_end TEXT NOT NULL DEFAULT '19:00',
    max_attempts INTEGER NOT NULL DEFAULT 3,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    approved_at TEXT,
    booking_link TEXT NOT NULL DEFAULT '',
    agent_persona TEXT NOT NULL DEFAULT 'friendly, concise, consultative sales assistant',
    opening_script TEXT NOT NULL DEFAULT '',
    qualification_questions_json TEXT NOT NULL DEFAULT '[]',
    objection_responses_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    phone_number TEXT NOT NULL DEFAULT '',
    phone_e164 TEXT NOT NULL DEFAULT '',
    timezone TEXT NOT NULL DEFAULT '',
    lead_source TEXT NOT NULL DEFAULT '',
    source_record_id TEXT NOT NULL DEFAULT '',
    consent_status TEXT NOT NULL DEFAULT '',
    consent_timestamp TEXT NOT NULL DEFAULT '',
    consent_text_or_url TEXT NOT NULL DEFAULT '',
    product_interest TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TEXT,
    suppressed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX IF NOT EXISTS idx_leads_campaign_status ON leads(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(client_id, phone_e164);

CREATE TABLE IF NOT EXISTS calls (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    lead_id TEXT,
    provider TEXT NOT NULL DEFAULT 'twilio',
    provider_call_id TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    local_time_at_dial TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    outcome TEXT,
    opt_out_detected INTEGER NOT NULL DEFAULT 0,
    transferred INTEGER NOT NULL DEFAULT 0,
    recording_url TEXT,
    cost_estimate_usd REAL NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE INDEX IF NOT EXISTS idx_calls_provider_call_id ON calls(provider_call_id);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL,
    speaker TEXT NOT NULL,
    text TEXT NOT NULL,
    started_at_ms INTEGER,
    ended_at_ms INTEGER,
    confidence REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (call_id) REFERENCES calls(id)
);

CREATE TABLE IF NOT EXISTS suppression_entries (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    phone_e164 TEXT NOT NULL,
    reason TEXT NOT NULL,
    source_call_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (client_id, phone_e164),
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL DEFAULT '',
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

