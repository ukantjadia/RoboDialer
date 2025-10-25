from .lead_model import db
from sqlalchemy import text

def ensure_audit_log_infrastructure(db):
    """Set up the audit log table, functions, and triggers in PostgreSQL"""
    conn = db.engine.connect()
    
    try:
        # SQL to create audit log infrastructure
        sql = text('''
        -- Drop the existing audit log table and trigger if they exist
        DROP TRIGGER IF EXISTS lead_audit_trigger ON leads;
        DROP FUNCTION IF EXISTS audit_lead_changes() CASCADE;
        DROP TABLE IF EXISTS lead_audit_log;

        -- 1. Create the audit log table
        CREATE TABLE IF NOT EXISTS lead_audit_log (
            id SERIAL PRIMARY KEY,
            table_name TEXT NOT NULL,
            row_id TEXT NOT NULL,
            column_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            username TEXT NOT NULL,
            changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Create a function to set the application user
        CREATE OR REPLACE FUNCTION set_app_user(username TEXT) RETURNS VOID AS $$
        BEGIN
            PERFORM set_config('app.current_user', username, FALSE);
        END;
        $$ LANGUAGE plpgsql;

        -- 3. Create the audit trigger function
        CREATE OR REPLACE FUNCTION audit_lead_changes() RETURNS TRIGGER AS $$
        DECLARE
            app_user TEXT;
            col_name TEXT;
            old_val TEXT;
            new_val TEXT;
        BEGIN
            app_user := current_setting('app.current_user', TRUE);
            IF app_user IS NULL THEN
                app_user := session_user;
            END IF;

            -- Special handling for soft delete
            IF NEW.deleted = TRUE AND OLD.deleted = FALSE THEN
                EXECUTE format('INSERT INTO lead_audit_log (table_name, row_id, column_name, old_value, new_value, username, changed_at) VALUES (%L, %L, %L, %L, %L, %L, now())',
                    TG_TABLE_NAME,
                    OLD.lead_id,
                    'LEAD_DELETED',
                    'false',
                    'true',
                    app_user
                );
            END IF;

            FOR col_name IN SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = TG_TABLE_NAME 
                            AND table_schema = TG_TABLE_SCHEMA
            LOOP
                -- Skip updated_at column
                IF col_name = 'updated_at' THEN
                    CONTINUE;
                END IF;
                BEGIN
                    EXECUTE format('SELECT ($1).%I::text', col_name) INTO old_val USING OLD;
                    EXECUTE format('SELECT ($1).%I::text', col_name) INTO new_val USING NEW;
                    IF old_val IS DISTINCT FROM new_val THEN
                        EXECUTE format('INSERT INTO lead_audit_log (table_name, row_id, column_name, old_value, new_value, username, changed_at) VALUES (%L, %L, %L, %L, %L, %L, now())',
                            TG_TABLE_NAME,
                            OLD.lead_id,
                            col_name,
                            old_val,
                            new_val,
                            app_user
                        );
                    END IF;
                EXCEPTION WHEN undefined_column THEN
                    NULL;
                END;
            END LOOP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        ''')
        
        conn.execute(sql)
        
        # Create the trigger after tables exist
        trigger_sql = text('''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'leads_audit_trigger'
            ) THEN
                EXECUTE 'CREATE TRIGGER leads_audit_trigger AFTER UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION audit_lead_changes();';
            END IF;
        EXCEPTION WHEN undefined_table THEN
            -- Table doesn't exist yet, which is fine
            RAISE NOTICE 'Table "leads" does not exist yet, trigger creation skipped.';
        END $$;
        ''')
        
        conn.execute(trigger_sql)
        conn.commit()
        
        print("Audit log infrastructure set up successfully")
    
    except Exception as e:
        conn.rollback()
        print(f"[Audit log setup] Warning: {e}")
    
    finally:
        conn.close()

class LeadAuditLog(db.Model):
    """Model for audit log entries"""
    __tablename__ = 'lead_audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False)
    row_id = db.Column(db.String(100), nullable=False)
    column_name = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    username = db.Column(db.String(100), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    
    def __repr__(self):
        return f'<AuditLog {self.id}: {self.table_name} #{self.row_id} {self.column_name}>' 