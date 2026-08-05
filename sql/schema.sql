
DO $$ BEGIN
    CREATE TYPE issue_status AS ENUM ('open', 'in_progress', 'resolved');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS tickets (
ticket_id UUID PRIMARY KEY DEFAULT gen_random_uuid()
, title VARCHAR(255) NOT NULL 
, status issue_status DEFAULT 'open' NOT NULL
, created_by TEXT NOT NULL DEFAULT 'unknown'
, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
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
