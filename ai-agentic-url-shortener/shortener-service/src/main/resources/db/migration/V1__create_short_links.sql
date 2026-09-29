CREATE TABLE short_links (
    code VARCHAR(32) PRIMARY KEY,
    target_url VARCHAR(2048) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    click_count BIGINT NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ NULL,
    version BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_short_links_active_expiry ON short_links(active, expires_at);
