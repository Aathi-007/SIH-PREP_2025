import os
import sqlite3
import pandas as pd
import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler

def main():
    db_path = 'data/ueba.db'
    model_path = 'data/isolation_forest_model.joblib'
    encoder_path = 'data/encoders.joblib'
    
    # Check file existence and sizes
    print("--- File Info ---")
    if os.path.exists(model_path):
        print(f"Model exists: {model_path} ({os.path.getsize(model_path)} bytes)")
    else:
        print(f"Model missing: {model_path}")
        
    if os.path.exists(encoder_path):
        print(f"Encoders exist: {encoder_path} ({os.path.getsize(encoder_path)} bytes)")
    else:
        print(f"Encoders missing: {encoder_path}")

    # Load data
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM activity_logs", conn)
    conn.close()
    
    # Load model and encoders
    model = joblib.load(model_path)
    encoders = joblib.load(encoder_path)
    
    # Engineer features
    df['department_mismatch'] = (df['accessed_department'] != df['department']).astype(int)
    df['location_encoded'] = encoders['location'].transform(df['location'])
    df['device_encoded'] = encoders['device'].transform(df['device_id'])
    
    feature_cols = ['download_mb', 'login_hour', 'location_encoded', 'device_encoded', 'department_mismatch', 'files_accessed']
    
    # Score
    scores = model.decision_function(df[feature_cols])
    inverted_scores = -scores
    scaler = MinMaxScaler(feature_range=(0, 100))
    df['ml_anomaly_score'] = np.round(scaler.fit_transform(inverted_scores.reshape(-1, 1)).flatten(), 2)
    
    # 1. Output from evaluate_model()
    print("\n--- Evaluate Model Output ---")
    known_anomalies = df[df['is_anomaly'].isin([1, True, 'True', '1'])]
    total_anomalies = len(known_anomalies)
    detected = known_anomalies[known_anomalies['ml_anomaly_score'] > 70]
    num_detected = len(detected)
    percentage = (num_detected / total_anomalies) * 100 if total_anomalies > 0 else 0
    print(f"{num_detected} out of {total_anomalies} known anomalies detected ({percentage:.1f}%)")
    
    # 2. Top 15 rows sorted by ml_anomaly_score desc
    print("\n--- Top 15 Rows by ml_anomaly_score ---")
    top_15 = df.sort_values('ml_anomaly_score', ascending=False).head(15)
    cols = ['user_id', 'timestamp', 'download_mb', 'login_hour', 'location', 'device_id', 'accessed_department', 'is_anomaly', 'ml_anomaly_score']
    print(top_15[cols].to_string(index=False))
    
    # 3. False anomalies in top 15
    print("\n--- False Anomalies in Top 15 ---")
    false_anomalies = top_15[top_15['is_anomaly'].isin([0, False, 'False', '0'])]
    print(f"Out of the top 15 highest ml_anomaly_score rows, {len(false_anomalies)} have is_anomaly = False.")
    if len(false_anomalies) > 0:
        print("These specific rows are:")
        print(false_anomalies[cols].to_string(index=False))

if __name__ == '__main__':
    main()
