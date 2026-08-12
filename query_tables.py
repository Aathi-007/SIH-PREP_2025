import sqlite3
import os

def main():
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'ueba.db')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. List all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")
            
        print("\nRow counts:")
        # 2. Count rows in specific tables
        target_tables = ['activity_logs', 'user_baselines', 'risk_events']
        for table in target_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table}: {count} rows")
            except sqlite3.OperationalError as e:
                print(f"{table}: Error - {e}")
                
    except Exception as e:
        print(f"Error connecting to or querying the database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    main()
