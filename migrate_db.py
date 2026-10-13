import sqlite3
import os

def migrate_database(db_path=None):
    if not db_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instance', 'database.db')

    if not os.path.exists(db_path):
        print(f"[*] Database file does not exist at {db_path}. It will be initialized on app start.")
        return

    print(f"[*] Checking database schema at {db_path}...")
    conn = sqlite3.connect(db_path)
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
            ("service_notes", "TEXT")
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
