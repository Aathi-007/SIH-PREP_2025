import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta
import os

fake = Faker()
Faker.seed(42)
random.seed(42)

DEPARTMENTS = ['HR', 'Finance', 'Engineering', 'Sales', 'IT']

def generate_users(num_users=30):
    """Generates a list of users with their baseline behaviors."""
    users = []
    for i in range(1, num_users + 1):
        user_id = f"U{i:03d}"
        user_name = fake.name()
        department = random.choice(DEPARTMENTS)
        
        # 1-2 usual cities
        num_cities = random.randint(1, 2)
        usual_cities = [fake.city() for _ in range(num_cities)]
        
        # 1-2 usual device IDs
        num_devices = random.randint(1, 2)
        usual_devices = [fake.uuid4()[:8] for _ in range(num_devices)]
        
        # Usual IP addresses per user (one per device)
        usual_ips = [fake.ipv4() for _ in range(num_devices)]
        
        # Download pattern: average download size for this user (5 to 50MB)
        avg_download = random.uniform(5.0, 50.0)
        
        users.append({
            'user_id': user_id,
            'user_name': user_name,
            'department': department,
            'usual_cities': usual_cities,
            'usual_devices': usual_devices,
            'usual_ips': usual_ips,
            'avg_download': avg_download,
            'is_dormant_candidate': False
        })
    return users

def generate_normal_events(users, start_date, num_days=90):
    """Generates normal activity events for all users over the specified period."""
    events = []
    
    # Pick one user to be the dormant account (will have NO activity for 30+ days)
    dormant_user = random.choice(users)
    dormant_user['is_dormant_candidate'] = True
    # Dormant from day 30 to day 65 (35 days of no activity)
    dormant_start = 30
    dormant_end = 65
    
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        is_weekend = current_date.weekday() >= 5
        
        for user in users:
            # Skip generating events if user is in their dormant period
            if user['is_dormant_candidate'] and dormant_start <= day <= dormant_end:
                continue
                
            # Determine number of events today
            if is_weekend:
                # Fewer or no events on weekends
                num_events = random.choices([0, 1, 2], weights=[0.8, 0.15, 0.05])[0]
            else:
                # 3-6 events per working day
                num_events = random.randint(3, 6)
                
            for _ in range(num_events):
                # Working hours mostly between 8-19, using triangular distribution centered at 10 AM
                hour = int(random.triangular(8, 19, 10))
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                timestamp = current_date.replace(hour=hour, minute=minute, second=second)
                
                # Normal location, device and IP
                location = random.choice(user['usual_cities'])
                device_idx = random.randint(0, len(user['usual_devices']) - 1)
                device_id = user['usual_devices'][device_idx]
                ip_address = user['usual_ips'][device_idx]
                
                # Download MB: average + small variation (e.g. +/- 20%)
                download_mb = max(0.1, random.gauss(user['avg_download'], user['avg_download'] * 0.2))
                
                files_accessed = random.randint(1, 10)
                
                # Accessed department (90% own department)
                if random.random() < 0.90:
                    accessed_department = user['department']
                else:
                    other_deps = [d for d in DEPARTMENTS if d != user['department']]
                    accessed_department = random.choice(other_deps) if other_deps else user['department']
                
                events.append({
                    'user_id': user['user_id'],
                    'user_name': user['user_name'],
                    'department': user['department'],
                    'timestamp': timestamp,
                    'login_hour': hour,
                    'location': location,
                    'ip_address': ip_address,
                    'device_id': device_id,
                    'download_mb': round(download_mb, 2),
                    'files_accessed': files_accessed,
                    'accessed_department': accessed_department,
                    'is_anomaly': False,
                    'anomaly_reason': '' # Internal field for our tracking
                })
                
    return events, dormant_user

def inject_anomalies(events, users, dormant_user, start_date):
    """Modifies some normal events into anomalies and adds specific anomalous events."""
    anomalies = []
    
    # Sort events by timestamp before picking random indices to ensure consistency
    events.sort(key=lambda x: x['timestamp'])
    
    # Helper to find a random event index that hasn't been modified yet
    used_indices = set()
    def get_random_event_idx():
        candidates = [i for i, e in enumerate(events) if i not in used_indices]
        if candidates:
            idx = random.choice(candidates)
            used_indices.add(idx)
            return idx
        return -1

    # 1. At least 2 events with huge download (2000-6000 MB)
    for _ in range(2):
        idx = get_random_event_idx()
        if idx != -1:
            events[idx]['download_mb'] = round(random.uniform(2000, 6000), 2)
            events[idx]['is_anomaly'] = True
            events[idx]['anomaly_reason'] = 'Massive download spike (Data Exfiltration)'
            anomalies.append(events[idx])
            
    # 2. At least 2 events with late night login (0-4 AM)
    for _ in range(2):
        idx = get_random_event_idx()
        if idx != -1:
            hour = random.randint(0, 4)
            events[idx]['login_hour'] = hour
            events[idx]['timestamp'] = events[idx]['timestamp'].replace(hour=hour)
            events[idx]['is_anomaly'] = True
            events[idx]['anomaly_reason'] = 'Unusual late night login'
            anomalies.append(events[idx])
            
    # 3. At least 2 events with unusual location (at least one distant/foreign)
    foreign_cities = ['Pyongyang', 'Moscow', 'Tehran', 'Beijing']
    for i in range(2):
        idx = get_random_event_idx()
        if idx != -1:
            if i == 0:
                events[idx]['location'] = random.choice(foreign_cities)
                events[idx]['anomaly_reason'] = 'Login from a known distant/foreign city (Impossible Travel)'
            else:
                events[idx]['location'] = fake.city() # random US/local city not in their usual list
                events[idx]['anomaly_reason'] = 'Login from an unusual city'
            events[idx]['is_anomaly'] = True
            anomalies.append(events[idx])
            
    # 4. At least 1 event with unusual device ID
    idx = get_random_event_idx()
    if idx != -1:
        events[idx]['device_id'] = 'UNKN-' + fake.uuid4()[:4]
        events[idx]['is_anomaly'] = True
        events[idx]['anomaly_reason'] = 'Login from an unrecognized device'
        anomalies.append(events[idx])
        
    # 5. At least 1 event with completely different accessed department
    idx = get_random_event_idx()
    if idx != -1:
        user_dept = events[idx]['department']
        other_deps = [d for d in DEPARTMENTS if d != user_dept]
        if other_deps:
            events[idx]['accessed_department'] = random.choice(other_deps)
            events[idx]['is_anomaly'] = True
            events[idx]['anomaly_reason'] = 'Accessed files from a completely different department (Lateral Movement)'
            anomalies.append(events[idx])
            
    # 6. At least 1 event simulating a "dormant account" sudden activity
    # dormant_user was dormant from day 30 to 65. Let's add a sudden event on day 66.
    dormant_event_date = start_date + timedelta(days=66)
    dormant_event = {
        'user_id': dormant_user['user_id'],
        'user_name': dormant_user['user_name'],
        'department': dormant_user['department'],
        'timestamp': dormant_event_date.replace(hour=14, minute=30, second=0),
        'login_hour': 14,
        'location': dormant_user['usual_cities'][0],
        'ip_address': dormant_user['usual_ips'][0],
        'device_id': dormant_user['usual_devices'][0],
        'download_mb': round(dormant_user['avg_download'], 2),
        'files_accessed': 2,
        'accessed_department': dormant_user['department'],
        'is_anomaly': True,
        'anomaly_reason': 'Sudden activity after 30+ days of dormancy'
    }
    events.append(dormant_event)
    anomalies.append(dormant_event)
    
    return events, anomalies

def save_to_csv(df, output_path):
    """Saves the dataframe to a CSV file."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

def main():
    print("Initializing Data Generator...")
    
    # 1. Generate users
    users = generate_users(num_users=30)
    
    # 2. Generate normal events for 90 days
    start_date = datetime.now() - timedelta(days=90)
    events, dormant_user = generate_normal_events(users, start_date, num_days=90)
    
    # 3. Inject anomalies
    events, anomalies = inject_anomalies(events, users, dormant_user, start_date)
    
    # 4. Format into DataFrame
    df = pd.DataFrame(events)
    # Sort by timestamp chronologically
    df.sort_values(by='timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Keep only the requested columns for the final dataset (plus is_anomaly)
    final_columns = [
        'user_id', 'user_name', 'department', 'timestamp', 'login_hour', 
        'location', 'ip_address', 'device_id', 'download_mb', 'files_accessed', 
        'accessed_department', 'is_anomaly'
    ]
    df_out = df[final_columns]
    
    # 5. Save to CSV
    # __file__ gives the script's path (backend/data_generator.py), so dirname is backend/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_dir, 'data', 'activity_logs.csv')
    save_to_csv(df_out, output_path)
    
    # 6. Output Summary
    print("\n" + "="*50)
    print("DATA GENERATION COMPLETE")
    print("="*50)
    print(f"Total rows generated: {len(df_out)}")
    print(f"Total anomalies injected: {len(anomalies)}")
    print(f"Output saved to: {output_path}")
    
    print("\n--- Preview of first 10 rows ---")
    print(df_out.head(10).to_string())
    
    print("\n" + "="*50)
    print("INJECTED ANOMALIES LIST")
    print("="*50)
    df_anomalies = pd.DataFrame(anomalies)
    df_anomalies.sort_values(by='timestamp', inplace=True)
    for i, row in df_anomalies.iterrows():
        print(f"User ID    : {row['user_id']}")
        print(f"Name       : {row['user_name']}")
        print(f"Time       : {row['timestamp']}")
        print(f"Reason     : {row['anomaly_reason']}")
        print("-" * 30)

if __name__ == "__main__":
    main()
