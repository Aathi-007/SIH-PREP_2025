import os
import sqlite3
import pandas as pd
from database import get_connection, CSV_PATH
from auth import get_password_hash

def seed_users():
    print("Seeding users into the database...")
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file not found at {CSV_PATH}")
        return

    # Extract unique users from activity_logs.csv
    df = pd.read_csv(CSV_PATH)
    unique_users = df[['user_id', 'user_name', 'department']].drop_duplicates(subset=['user_id'])
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Clear existing users for idempotency during dev
        cursor.execute("DELETE FROM users")
        
        inserted_users = []
        default_password = "password123"
        hashed_pw = get_password_hash(default_password)
        
        for _, row in unique_users.iterrows():
            user_id = row['user_id']
            # Generate a username based on user_name or user_id
            if pd.notnull(row['user_name']) and row['user_name'].strip():
                username = row['user_name'].replace(" ", ".").lower()
            else:
                username = f"user.{user_id.lower()}"
                
            department = row['department'] if pd.notnull(row['department']) else 'Unknown'
            role = 'employee'
            
            # Insert into users table
            insert_sql = '''
                INSERT INTO users (user_id, username, password_hash, department, role)
                VALUES (?, ?, ?, ?, ?)
            '''
            try:
                cursor.execute(insert_sql, (user_id, username, hashed_pw, department, role))
                inserted_users.append({
                    "user_id": user_id,
                    "username": username,
                    "department": department,
                    "password": default_password
                })
            except sqlite3.IntegrityError:
                # Handle potential duplicate usernames if any
                print(f"Warning: Could not insert user {username} (maybe duplicate).")
                continue
                
        conn.commit()
        
        print(f"\nSuccessfully seeded {len(inserted_users)} users.")
        print("\n--- User Credentials ---")
        for u in inserted_users:
            print(f"Username: {u['username']} | Password: {u['password']} | Dept: {u['department']}")
        print("------------------------\n")
        
    finally:
        conn.close()

if __name__ == "__main__":
    seed_users()
