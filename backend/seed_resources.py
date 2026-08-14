import sqlite3
from database import get_connection

def seed_resources():
    print("Seeding resources into the database...")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Clear existing resources and access_violations for idempotency during dev
        cursor.execute("DELETE FROM access_violations")
        cursor.execute("DELETE FROM resources")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='access_violations'")
        
        resources_to_insert = [
            ("RES001", "Q3_financials.xlsx", "Finance", "confidential"),
            ("RES002", "employee_records.db", "HR", "confidential"),
            ("RES003", "source_code_repo.zip", "Engineering", "internal"),
            ("RES004", "marketing_assets.png", "Sales", "public"),
            ("RES005", "server_configs.txt", "IT", "internal"),
            ("RES006", "budget_draft.pdf", "Finance", "internal"),
            ("RES007", "onboarding_guide.pdf", "HR", "public"),
            ("RES008", "client_contacts.csv", "Sales", "confidential"),
            ("RES009", "api_keys.env", "Engineering", "confidential"),
            ("RES010", "network_topology.vsdx", "IT", "confidential")
        ]
        
        insert_sql = '''
            INSERT INTO resources (resource_id, resource_name, owning_department, sensitivity)
            VALUES (?, ?, ?, ?)
        '''
        
        cursor.executemany(insert_sql, resources_to_insert)
        conn.commit()
        
        print(f"\nSuccessfully seeded {len(resources_to_insert)} resources.")
        print("\n--- Resources ---")
        for res in resources_to_insert:
            print(f"ID: {res[0]:<7} | Dept: {res[2]:<11} | Name: {res[1]:<22} | Sensitivity: {res[3]}")
        print("-----------------\n")
        
    except Exception as e:
        print(f"Error seeding resources: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_resources()
