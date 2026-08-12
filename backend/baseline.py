import pandas as pd
import numpy as np
from datetime import datetime
from database import get_connection

def build_user_baselines():
    """
    Builds baseline behavioral profiles for each user based on historical activity logs.
    Excludes anomalies (where is_anomaly = 1) from the baseline calculations.
    """
    conn = get_connection()
    
    try:
        # Load activity_logs excluding anomalies
        # EXPLANATION: We exclude anomalies because we want the baseline to represent 
        # TRUE normal behavior, not be polluted by the anomalies we deliberately injected. 
        # In a real production system we wouldn't have this label, but since we control 
        # the synthetic data, we use it now to build clean baselines.
        query = "SELECT * FROM activity_logs WHERE is_anomaly = 0"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No normal activity logs found to build baselines.")
            return 0
            
        baselines = []
        
        # Group by user_id
        for user_id, user_data in df.groupby('user_id'):
            # a. Calculate avg_download_mb
            avg_download_mb = user_data['download_mb'].mean()
            
            # b. Calculate std_download_mb (use 0 if only one event exists)
            if len(user_data) > 1:
                std_download_mb = user_data['download_mb'].std(ddof=1)
            else:
                std_download_mb = 0.0
                
            # c. Calculate usual_login_hour_start and usual_login_hour_end
            # 5th percentile and 95th percentile
            usual_login_hour_start = int(np.percentile(user_data['login_hour'], 5))
            usual_login_hour_end = int(np.percentile(user_data['login_hour'], 95))
            
            # d. Calculate known_locations
            total_events = len(user_data)
            location_counts = user_data['location'].value_counts()
            valid_locations = location_counts[location_counts > 0.05 * total_events].index.tolist()
            known_locations = ",".join(valid_locations)
            
            # e. Calculate known_devices
            device_counts = user_data['device_id'].value_counts()
            valid_devices = device_counts[device_counts > 0.05 * total_events].index.tolist()
            known_devices = ",".join(valid_devices)
            
            # f. Calculate usual_department (most frequent)
            usual_department = user_data['accessed_department'].mode().iloc[0] if not user_data['accessed_department'].mode().empty else ""
            
            # g. Set last_updated
            last_updated = datetime.now().isoformat()
            
            baselines.append((
                user_id, float(avg_download_mb), float(std_download_mb),
                usual_login_hour_start, usual_login_hour_end,
                known_locations, known_devices, usual_department, last_updated
            ))
            
        # 4. Insert or update (upsert) each user's calculated baseline
        cursor = conn.cursor()
        
        upsert_sql = '''
            INSERT INTO user_baselines (
                user_id, avg_download_mb, std_download_mb, usual_login_hour_start,
                usual_login_hour_end, known_locations, known_devices,
                usual_department, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                avg_download_mb=excluded.avg_download_mb,
                std_download_mb=excluded.std_download_mb,
                usual_login_hour_start=excluded.usual_login_hour_start,
                usual_login_hour_end=excluded.usual_login_hour_end,
                known_locations=excluded.known_locations,
                known_devices=excluded.known_devices,
                usual_department=excluded.usual_department,
                last_updated=excluded.last_updated
        '''
        
        cursor.executemany(upsert_sql, baselines)
        conn.commit()
        
        return len(baselines)
        
    except Exception as e:
        print(f"Error building baselines: {e}")
        return 0
    finally:
        conn.close()

def print_baseline_summary():
    """
    Prints a readable table showing all users' baselines for manual sanity-check.
    """
    conn = get_connection()
    try:
        query = "SELECT user_id, avg_download_mb, usual_login_hour_start, usual_login_hour_end, known_locations, known_devices, usual_department FROM user_baselines"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No baselines found.")
            return
            
        print("\nUser Baselines Summary:")
        print("-" * 80)
        
        # Formatting for a readable table
        df['login_hour_range'] = df['usual_login_hour_start'].astype(str) + " - " + df['usual_login_hour_end'].astype(str)
        
        # Select columns to display
        display_df = df[['user_id', 'avg_download_mb', 'login_hour_range', 'known_locations', 'known_devices', 'usual_department']].copy()
        display_df['avg_download_mb'] = display_df['avg_download_mb'].round(2)
        
        # Using string conversion instead of to_markdown which requires tabulate package
        print(display_df.to_string(index=False))
        
    except Exception as e:
        print(f"Error printing baseline summary: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Building user baselines...")
    num_users = build_user_baselines()
    
    if num_users > 0:
        print_baseline_summary()
        print(f"\nBaselines built for {num_users} users")
    else:
        print("\nFailed to build baselines or no users processed.")
