-- Lakebase schema for the support-ticketing system (Postgres dialect).
--
-- Fully idempotent: safe against a fresh database OR one that already has the
-- earlier version of these tables. The CREATE TABLE blocks cover the fresh
-- case; the ALTER TABLE blocks below migrate an existing install.

DO $$ BEGIN
    CREATE TYPE issue_status AS ENUM ('open', 'in_progress', 'resolved');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS tickets (
ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
, title VARCHAR(255) NOT NULL
, status issue_status DEFAULT 'open' NOT NULL
, priority ticket_priority DEFAULT 'medium' NOT NULL
, created_by TEXT NOT NULL DEFAULT 'unknown'
, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
-- Soft delete: NULL means live. Every read filters on deleted_at IS NULL, so
-- an archived ticket keeps its message history and can be restored.
, deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS ticket_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
    , ticket_id UUID NOT NULL
    , message_text TEXT NOT NULL
    , author TEXT NOT NULL DEFAULT 'unknown'
    , created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
    ,CONSTRAINT fk_tickets
        FOREIGN KEY(ticket_id)
        REFERENCES tickets(ticket_id)
        ON DELETE CASCADE);

-- Migration for databases created before priority / soft delete existed.
-- No-ops on a fresh database where CREATE TABLE already added the columns.
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority ticket_priority DEFAULT 'medium' NOT NULL;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- The list view always excludes archived rows; the detail view pulls a
-- ticket's thread in chronological order.
CREATE INDEX IF NOT EXISTS ix_tickets_live
    ON tickets (created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_ticket_messages_thread
    ON ticket_messages (ticket_id, created_at);
