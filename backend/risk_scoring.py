import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
from sklearn.preprocessing import MinMaxScaler
from database import get_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_PATH = os.path.join(DATA_DIR, 'isolation_forest_model.joblib')
ENCODER_PATH = os.path.join(DATA_DIR, 'encoders.joblib')

def calculate_rule_based_score(event, baseline):
    score = 0
    reasons = []
    
    # Unusual download volume
    if baseline['avg_download_mb'] > 0 and event['download_mb'] > 3 * baseline['avg_download_mb']:
        score += 25
        reasons.append("unusual_download_volume")
        
    # Unusual login time
    if not (baseline['usual_login_hour_start'] <= event['login_hour'] <= baseline['usual_login_hour_end']):
        score += 15
        reasons.append("unusual_login_time")
        
    # Unusual location
    known_locations = str(baseline['known_locations']).split(',')
    if event['location'] not in known_locations:
        score += 20
        reasons.append("unusual_location")
        
    # New device
    known_devices = str(baseline['known_devices']).split(',')
    if event['device_id'] not in known_devices:
        score += 15
        reasons.append("new_device")
        
    # Department mismatch
    if event['accessed_department'] != baseline['usual_department']:
        score += 25
        reasons.append("department_mismatch")
        
    score = min(score, 100)
    return score, reasons

def calculate_final_risk_score(event, baseline, ml_anomaly_score):
    rule_score, reasons = calculate_rule_based_score(event, baseline)
    
    final_score = (0.6 * rule_score) + (0.4 * ml_anomaly_score)
    final_score = int(np.round(final_score))
    final_score = min(final_score, 100)
    
    if ml_anomaly_score > 70:
        reasons.append("ml_model_flagged_unusual_pattern")
        
    return final_score, reasons

def score_all_events():
    conn = get_connection()
    try:
        # Load model and encoders
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODER_PATH)
        
        # Load activity_logs
        df_logs = pd.read_sql_query("SELECT * FROM activity_logs", conn)
        
        if df_logs.empty:
            print("No activity logs to score.")
            return
            
        # Calculate ml_anomaly_score
        df_ml = df_logs.copy()
        df_ml['department_mismatch'] = (df_ml['accessed_department'] != df_ml['department']).astype(int)
        
        # Transform categories using loaded encoders
        df_ml['location_encoded'] = encoders['location'].transform(df_ml['location'])
        df_ml['device_encoded'] = encoders['device'].transform(df_ml['device_id'])
        
        feature_cols = ['download_mb', 'login_hour', 'location_encoded', 'device_encoded', 'department_mismatch', 'files_accessed']
        
        scores = model.decision_function(df_ml[feature_cols])
        scaler = MinMaxScaler(feature_range=(0, 100))
        df_logs['ml_anomaly_score'] = scaler.fit_transform((-scores).reshape(-1, 1)).flatten()
        
        # Load baselines into dict for fast lookup
        df_base = pd.read_sql_query("SELECT * FROM user_baselines", conn)
        baselines_dict = df_base.set_index('user_id').to_dict('index')
        
        risk_events_to_insert = []
        now = datetime.now().isoformat()
        
        # Score each event
        for _, event in df_logs.iterrows():
            user_id = event['user_id']
            if user_id not in baselines_dict:
                continue
                
            baseline = baselines_dict[user_id]
            ml_score = event['ml_anomaly_score']
            
            final_score, reasons = calculate_final_risk_score(event, baseline, ml_score)
            
            if final_score > 40:
                reasons_str = ",".join(reasons)
                risk_events_to_insert.append((
                    event['event_id'], user_id, final_score, reasons_str, now, False
                ))
                
        # Insert into risk_events
        cursor = conn.cursor()
        cursor.execute("DELETE FROM risk_events") # Clear previous runs for idempotency
        
        insert_sql = '''
            INSERT INTO risk_events (event_id, user_id, risk_score, reasons, flagged_at, reviewed)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor.executemany(insert_sql, risk_events_to_insert)
        conn.commit()
        
        print(f"Scored all events. {len(risk_events_to_insert)} high-risk events flagged and stored.")
        
    except Exception as e:
        print(f"Error scoring events: {e}")
    finally:
        conn.close()

def evaluate_risk_scoring():
    conn = get_connection()
    try:
        # Check SQLite boolean mapping
        df_anomalies = pd.read_sql_query("SELECT event_id FROM activity_logs WHERE is_anomaly IN (1, 'True', '1')", conn)
        total_anomalies = len(df_anomalies)
        
        if total_anomalies == 0:
            print("No known anomalies found to evaluate.")
            return
            
        anomaly_event_ids = tuple(df_anomalies['event_id'].tolist())
        
        cursor = conn.cursor()
        if len(anomaly_event_ids) == 1:
            query = "SELECT COUNT(*) FROM risk_events WHERE risk_score > 60 AND event_id = ?"
            cursor.execute(query, (anomaly_event_ids[0],))
        else:
            placeholders = ','.join(['?'] * len(anomaly_event_ids))
            query = f"SELECT COUNT(*) FROM risk_events WHERE risk_score > 60 AND event_id IN ({placeholders})"
            cursor.execute(query, anomaly_event_ids)
        num_flagged = cursor.fetchone()[0]
        
        percentage = (num_flagged / total_anomalies) * 100
        print(f"{num_flagged} out of {total_anomalies} known anomalies flagged as high risk ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"Error evaluating risk scoring: {e}")
    finally:
        conn.close()

def main():
    print("Scoring all events and inserting high-risk alerts...")
    score_all_events()
    
    print("\nEvaluating risk scoring rules...")
    evaluate_risk_scoring()
    
    print("\nTop 15 Highest Risk Events:")
    print("-" * 80)
    
    conn = get_connection()
    try:
        query = "SELECT user_id, risk_score, reasons FROM risk_events ORDER BY risk_score DESC LIMIT 15"
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No risk events found.")
        else:
            print(df.to_string(index=False))
            
    except Exception as e:
        print(f"Error fetching top risk events: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
