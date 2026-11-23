-- Local SQLite schema for the RETECH e-waste marketplace.
-- Running this script more than once does not clear existing records.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'recycler', 'admin')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    device_condition TEXT NOT NULL,
    description TEXT NOT NULL,
    estimate INTEGER NOT NULL CHECK (estimate >= 0),
    status TEXT NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'reserved', 'sold', 'archived')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_listings_status_category
    ON listings(status, category, id);

CREATE TABLE IF NOT EXISTS buyback_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    buyer_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL CHECK (kind IN ('buyback', 'exchange')),
    offer INTEGER NOT NULL CHECK (offer >= 0),
    exchange_details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'declined', 'cancelled', 'completed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_requests_listing_status
    ON buyback_requests(listing_id, status);
CREATE INDEX IF NOT EXISTS idx_requests_buyer_status
    ON buyback_requests(buyer_id, status);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL UNIQUE REFERENCES buyback_requests(id),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
