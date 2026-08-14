import sqlite3
import pandas as pd
import os

# Define paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'ueba.db')
CSV_PATH = os.path.join(BASE_DIR, 'data', 'activity_logs.csv')

def get_connection():
    """
    Returns a connection to the SQLite database.
    Can be reused by other modules like baseline.py or risk_scoring.py.
    """
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # Enable foreign keys for SQLite
    conn.execute("PRAGMA foreign_keys = 1")
    return conn

def create_tables(conn):
    """
    Creates the necessary tables for the UEBA project.
    """
    cursor = conn.cursor()
    
    # Table: users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        department TEXT,
        role TEXT DEFAULT 'employee'
    )
    ''')

    # Table: resources
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resources (
        resource_id TEXT PRIMARY KEY,
        resource_name TEXT NOT NULL,
        owning_department TEXT,
        sensitivity TEXT
    )
    ''')

    # Table: access_violations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_violations (
        violation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        resource_id TEXT,
        requester_department TEXT,
        resource_department TEXT,
        attempted_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
    )
    ''')

    # Table 1: activity_logs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        user_name TEXT,
        department TEXT,
        timestamp TEXT,
        login_hour INTEGER,
        location TEXT,
        ip_address TEXT,
        device_id TEXT,
        download_mb REAL,
        files_accessed INTEGER,
        accessed_department TEXT,
        is_anomaly BOOLEAN
    )
    ''')
    
    # Create index on user_id and timestamp for fast lookups
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_user_time 
    ON activity_logs (user_id, timestamp)
    ''')
    
    # Table 2: user_baselines (Empty structure for now)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_baselines (
        user_id TEXT PRIMARY KEY,
        avg_download_mb REAL,
        std_download_mb REAL,
        usual_login_hour_start INTEGER,
        usual_login_hour_end INTEGER,
        known_locations TEXT,
        known_devices TEXT,
        usual_department TEXT,
        last_updated TEXT
    )
    ''')
    
    # Table 3: risk_events (Empty structure for now)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS risk_events (
        risk_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        user_id TEXT,
        risk_score INTEGER,
        reasons TEXT,
        flagged_at TEXT,
        reviewed BOOLEAN DEFAULT 0,
        FOREIGN KEY (event_id) REFERENCES activity_logs(event_id)
    )
    ''')
    
    conn.commit()

def load_csv_to_db(conn):
    """
    Reads the activity_logs.csv file and inserts it into the activity_logs table.
    It clears the table first to ensure duplicate-run safety.
    """
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return 0

    cursor = conn.cursor()
    
    # Duplicate-run safety: Clear the table and reset the autoincrement sequence
    cursor.execute("DELETE FROM risk_events")
    cursor.execute("DELETE FROM activity_logs")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='activity_logs'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='risk_events'")
    conn.commit()

    # Read CSV using pandas
    df = pd.read_csv(CSV_PATH)
    
    # Columns mapping exactly to the database schema (excluding event_id)
    columns = [
        'user_id', 'user_name', 'department', 'timestamp', 'login_hour', 
        'location', 'ip_address', 'device_id', 'download_mb', 'files_accessed', 
        'accessed_department', 'is_anomaly'
    ]
    
    # Ensure pandas uses standard python bool/int instead of numpy types if needed
    data_to_insert = df[columns].to_records(index=False).tolist()
    
    # Insert query using parameterized statements
    insert_sql = f'''
        INSERT INTO activity_logs ({', '.join(columns)})
        VALUES ({', '.join(['?'] * len(columns))})
    '''
    
    cursor.executemany(insert_sql, data_to_insert)
    conn.commit()
    
    return len(data_to_insert)

def main():
    print("Initializing UEBA Database...")
    conn = get_connection()
    
    try:
        # Create the tables
        create_tables(conn)
        print("Tables checked/created successfully.")
        
        # Load the CSV data
        print("Loading CSV data into activity_logs table...")
        rows_loaded = load_csv_to_db(conn)
        print(f"Total rows successfully loaded: {rows_loaded}")
        
        # Print summary
        print("\n" + "="*40)
        print("DATABASE SUMMARY")
        print("="*40)
        
        cursor = conn.cursor()
        tables = ['users', 'resources', 'access_violations', 'activity_logs', 'user_baselines', 'risk_events']
        
        for table in tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            exists = cursor.fetchone() is not None
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"Table '{table}' -> Exists (Row count: {count})")
            else:
                print(f"Table '{table}' -> MISSING")
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()
    
    print("\nDatabase initialization complete.")

if __name__ == "__main__":
    main()
