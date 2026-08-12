import sqlite3
import os

def main():
    db_path = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'ueba.db')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM activity_logs LIMIT 5")
        rows = cursor.fetchall()
        
        if not rows:
            print("No rows found.")
            return
            
        col_names = [description[0] for description in cursor.description]
        
        # Calculate column widths
        col_widths = [len(name) for name in col_names]
        for row in rows:
            for i, item in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(item)))
                
        # Print header
        header = " | ".join(f"{name:<{col_widths[i]}}" for i, name in enumerate(col_names))
        print(header)
        print("-" * len(header))
        
        # Print rows
        for row in rows:
            row_str = " | ".join(f"{str(item):<{col_widths[i]}}" for i, item in enumerate(row))
            print(row_str)
            
    except Exception as e:
        print(f"Error connecting to or querying the database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    main()
