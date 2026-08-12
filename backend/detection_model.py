import os
import sqlite3
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.ensemble import IsolationForest
import joblib
from database import get_connection

# Directory setup for saving models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_PATH = os.path.join(DATA_DIR, 'isolation_forest_model.joblib')
ENCODER_PATH = os.path.join(DATA_DIR, 'encoders.joblib')

def load_data():
    """Load activity logs into a pandas DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM activity_logs", conn)
    conn.close()
    return df

def engineer_features(df):
    """
    Convert raw columns into numeric features the model can use.
    """
    df = df.copy()
    
    # department_mismatch: binary feature (1 if accessed_department != department, else 0)
    df['department_mismatch'] = (df['accessed_department'] != df['department']).astype(int)
    
    location_encoder = LabelEncoder()
    device_encoder = LabelEncoder()
    
    # Encode location and device_id
    df['location_encoded'] = location_encoder.fit_transform(df['location'])
    df['device_encoded'] = device_encoder.fit_transform(df['device_id'])
    
    encoders = {
        'location': location_encoder,
        'device': device_encoder
    }
    
    feature_cols = ['download_mb', 'login_hour', 'location_encoded', 'device_encoded', 'department_mismatch', 'files_accessed']
    
    return df, encoders, feature_cols

def train_model(X_train):
    """
    Train the IsolationForest model.
    """
    # EXPLANATION: We train ONLY on rows where is_anomaly = False (the true normal behavior), 
    # so the model learns what "normal" looks like without being confused by the anomalies 
    # we deliberately injected. 
    # 
    # In a real production system without labels, we'd instead train on ALL data and rely 
    # on the fact that anomalies are naturally rare (isolation forest assumes anomalies 
    # are the minority, which typically works even without clean labels).
    
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(X_train)
    return model

def score_events(model, X_all):
    """
    Run model on full dataset. Convert decision_function output to a 0-100 anomaly score.
    """
    # decision_function: lower values are more anomalous, higher values are more normal
    scores = model.decision_function(X_all)
    
    # We want 100 = most anomalous, 0 = most normal
    # So we invert the scores (multiply by -1)
    inverted_scores = -scores
    
    # Min-max scaling to 0-100
    scaler = MinMaxScaler(feature_range=(0, 100))
    scaled_scores = scaler.fit_transform(inverted_scores.reshape(-1, 1))
    
    return np.round(scaled_scores.flatten(), 2)

def evaluate_model(df):
    """
    Check percentage of known anomalies that got an ml_anomaly_score > 70.
    """
    # SQLite boolean is typically 0 or 1. Let's handle both possible representations.
    known_anomalies = df[df['is_anomaly'].isin([1, True, 'True', '1'])]
    total_anomalies = len(known_anomalies)
    
    if total_anomalies == 0:
        print("No known anomalies in dataset to evaluate.")
        return
        
    detected = known_anomalies[known_anomalies['ml_anomaly_score'] > 70]
    num_detected = len(detected)
    percentage = (num_detected / total_anomalies) * 100
    
    print(f"{num_detected} out of {total_anomalies} known anomalies detected ({percentage:.1f}%)")

def main():
    print("Loading data...")
    df = load_data()
    
    print("Engineering features...")
    df, encoders, feature_cols = engineer_features(df)
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Save encoders
    joblib.dump(encoders, ENCODER_PATH)
    print(f"Saved encoders to {ENCODER_PATH}")
    
    # Filter training data (only normal behavior)
    train_mask = df['is_anomaly'].isin([0, False, 'False', '0'])
    X_train = df.loc[train_mask, feature_cols]
    
    print("Training IsolationForest model...")
    model = train_model(X_train)
    
    # Save model
    joblib.dump(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")
    
    print("Scoring all events...")
    X_all = df[feature_cols]
    df['ml_anomaly_score'] = score_events(model, X_all)
    
    print("\nModel Evaluation:")
    evaluate_model(df)
    
    print("\nTop 15 Highest ml_anomaly_score Rows:")
    top_15 = df.sort_values('ml_anomaly_score', ascending=False).head(15)
    
    # Format and print top 15
    cols_to_print = ['event_id', 'user_id', 'timestamp', 'ml_anomaly_score', 'download_mb', 'files_accessed', 'department_mismatch', 'is_anomaly']
    print(top_15[cols_to_print].to_string(index=False))

if __name__ == '__main__':
    main()
