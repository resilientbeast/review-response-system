-- migrations/001_initial.sql

CREATE TABLE businesses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand_voice_json TEXT,  -- JSON blob of brand voice guidelines
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL REFERENCES businesses(id),
    platform TEXT NOT NULL,
    rating INTEGER NOT NULL,
    text TEXT NOT NULL,
    author TEXT,
    review_timestamp TEXT,
    ingested_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE responses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    review_id TEXT NOT NULL REFERENCES reviews(id),
    response_text TEXT NOT NULL,
    qa_score REAL,
    approved_by TEXT,           -- 'auto' or human identifier
    published_at TEXT,
    version INTEGER DEFAULT 1
);

CREATE TABLE response_tone_tags (
    response_id TEXT NOT NULL REFERENCES responses(id),
    tag TEXT NOT NULL           -- e.g. 'empathetic', 'solution_first', 'warm_opener'
);

CREATE INDEX idx_responses_business ON responses(review_id);
CREATE INDEX idx_reviews_business ON reviews(business_id);
