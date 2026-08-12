import sqlite3
import pandas as pd

def main():
    conn = sqlite3.connect('a:/SiH/backend/data/ueba.db')
    
    # 1. Output from evaluate_risk_scoring()
    df_anomalies = pd.read_sql_query("SELECT event_id FROM activity_logs WHERE is_anomaly = 1", conn)
    total_anomalies = len(df_anomalies)
    if total_anomalies > 0:
        anomaly_event_ids = tuple(df_anomalies['event_id'].tolist())
        if len(anomaly_event_ids) == 1:
             query = f"SELECT COUNT(*) FROM risk_events WHERE risk_score > 60 AND event_id = {anomaly_event_ids[0]}"
        else:
             query = f"SELECT COUNT(*) FROM risk_events WHERE risk_score > 60 AND event_id IN {anomaly_event_ids}"
        num_flagged = pd.read_sql_query(query, conn).iloc[0, 0]
        percentage = (num_flagged / total_anomalies) * 100
        print(f"--- 1. Evaluate Risk Scoring ---")
        print(f"{num_flagged} out of {total_anomalies} known anomalies flagged as high risk ({percentage:.1f}%)\n")
    
    # 2. Top 15 from risk_events
    print("--- 2. Top 15 Highest Risk Events ---")
    query_top = "SELECT user_id, risk_score, reasons, event_id FROM risk_events ORDER BY risk_score DESC LIMIT 15"
    top_15 = pd.read_sql_query(query_top, conn)
    print(top_15[['user_id', 'risk_score', 'reasons']].to_string(index=False))
    print()
    
    # 3. Single highest risk score row full details
    if not top_15.empty:
        highest_event = top_15.iloc[0]
        event_id = highest_event['event_id']
        user_id = highest_event['user_id']
        
        print("--- 3. Verification of Highest Risk Event ---")
        print("[Risk Event Data]")
        print(f"Risk Score: {highest_event['risk_score']}")
        print(f"Reasons:    {highest_event['reasons']}")
        print()
        
        print("[Raw Activity Log Data]")
        raw_log = pd.read_sql_query(f"SELECT download_mb, login_hour, location, device_id, accessed_department FROM activity_logs WHERE event_id = {event_id}", conn).iloc[0]
        print(f"Download MB:         {raw_log['download_mb']}")
        print(f"Login Hour:          {raw_log['login_hour']}")
        print(f"Location:            {raw_log['location']}")
        print(f"Device ID:           {raw_log['device_id']}")
        print(f"Accessed Department: {raw_log['accessed_department']}")
        print()
        
        print("[User Baseline Data]")
        baseline = pd.read_sql_query(f"SELECT avg_download_mb, usual_login_hour_start, usual_login_hour_end, known_locations, known_devices, usual_department FROM user_baselines WHERE user_id = '{user_id}'", conn).iloc[0]
        print(f"Avg Download MB:        {baseline['avg_download_mb']}")
        print(f"Usual Login Hours:      {baseline['usual_login_hour_start']} to {baseline['usual_login_hour_end']}")
        print(f"Known Locations:        {baseline['known_locations']}")
        print(f"Known Devices:          {baseline['known_devices']}")
        print(f"Usual Department:       {baseline['usual_department']}")
        print()
        
    # 4. Total row counts
    print("--- 4. Total Row Counts ---")
    total_risk = pd.read_sql_query("SELECT COUNT(*) FROM risk_events", conn).iloc[0, 0]
    total_activity = pd.read_sql_query("SELECT COUNT(*) FROM activity_logs", conn).iloc[0, 0]
    print(f"Total rows in risk_events:   {total_risk}")
    print(f"Total rows in activity_logs: {total_activity}")

    conn.close()

if __name__ == '__main__':
    main()
