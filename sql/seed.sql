-- Sample data for the support-ticketing system.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM tickets) THEN

        WITH new_tickets AS (
            INSERT INTO tickets (title, status, created_by) VALUES
                ('Cannot log in to Databricks workspace',
                    'open',        'alice@example.com'),
                ('Lakebase connection times out from Databricks App',
                    'in_progress', 'bob@example.com'),
                ('How do I schedule a Delta Live Tables job?',
                    'resolved',    'carol@example.com')
            RETURNING ticket_id, title
        )
        INSERT INTO ticket_messages (ticket_id, message_text, author)
        SELECT t.ticket_id, m.message_text, m.author
        FROM new_tickets t
        JOIN (VALUES
            -- Ticket 1: login issue (open, 2 messages)
            ('Cannot log in to Databricks workspace',
             'I keep getting a 403 after entering my SSO credentials. Started this morning.',
             'alice@example.com'),
            ('Cannot log in to Databricks workspace',
             'Which browser are you using? Can you share the error page URL and any request-id in the error text?',
             'support@example.com'),

            -- Ticket 2: Lakebase timeout (in_progress, 3 messages)
            ('Lakebase connection times out from Databricks App',
             'App logs show psycopg2.OperationalError: connection timed out when calling get_connection().',
             'bob@example.com'),
            ('Lakebase connection times out from Databricks App',
             'Looking now. Can you confirm your Lakebase instance is not paused? Autoscaling projects scale to zero after 24h idle.',
             'support@example.com'),
            ('Lakebase connection times out from Databricks App',
             'You are right — instance was paused. Woke it up and the app connects. Leaving open until we add a keep-alive.',
             'bob@example.com'),

            -- Ticket 3: DLT scheduling (resolved, 2 messages)
            ('How do I schedule a Delta Live Tables job?',
             'I want my pipeline to run every hour. What is the recommended way?',
             'carol@example.com'),
            ('How do I schedule a Delta Live Tables job?',
             'Open the pipeline, click Settings → Schedule, and pick "Cron" with expression `0 * * * *`. Docs: https://docs.databricks.com/delta-live-tables/schedule.html',
             'support@example.com')
        ) AS m(title, message_text, author)
          ON t.title = m.title;

    END IF;
END $$;
