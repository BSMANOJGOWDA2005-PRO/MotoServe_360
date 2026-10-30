import sqlite3
import os

def migrate_database(db_path=None):
    if not db_path:
        try:
            from flask import current_app
            if current_app and current_app.config.get('SQLALCHEMY_DATABASE_URI'):
                uri = current_app.config['SQLALCHEMY_DATABASE_URI']
                if uri.startswith('sqlite:///'):
                    db_path = uri.replace('sqlite:///', '')
        except Exception:
            pass

    if not db_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instance', 'database.db')

    # If using non-sqlite db or file doesn't exist yet
    if not os.path.exists(db_path):
        print(f"[*] Database file does not exist at {db_path}. Skipping sqlite manual migrations.")
        return

    print(f"[*] Checking database schema at {db_path}...")
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"[*] Could not open sqlite database at {db_path}: {e}")
        return

    cursor = conn.cursor()

    try:
        # Check if table service_requests exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_requests'")
        if not cursor.fetchone():
            print("[*] Table service_requests not yet created. Will be created by SQLAlchemy.")
            return

        cursor.execute("PRAGMA table_info(service_requests)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        cols_to_add = [
            ("locality", "VARCHAR(100)"),
            ("provider_name", "VARCHAR(150)"),
            ("provider_lat", "FLOAT"),
            ("provider_lng", "FLOAT"),
            ("provider_address", "VARCHAR(255)"),
            ("provider_phone", "VARCHAR(50)"),
            ("provider_source", "VARCHAR(20) DEFAULT 'registered'"),
            ("distance_km", "FLOAT"),
            ("service_notes", "TEXT"),
            ("platform_fee", "FLOAT DEFAULT 9.0")
        ]

        added = 0
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                print(f"[+] Adding column {col_name} ({col_type}) to service_requests...")
                cursor.execute(f"ALTER TABLE service_requests ADD COLUMN {col_name} {col_type}")
                added += 1

        conn.commit()
        if added > 0:
            print(f"[OK] Successfully migrated database: added {added} new column(s).")
        else:
            print("[OK] Database schema is already up to date.")
    except Exception as e:
        print(f"[!] Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()
