import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import joblib
from sklearn.preprocessing import MinMaxScaler
import uvicorn

from database import get_connection
from risk_scoring import calculate_rule_based_score, calculate_final_risk_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_PATH = os.path.join(DATA_DIR, 'isolation_forest_model.joblib')
ENCODER_PATH = os.path.join(DATA_DIR, 'encoders.joblib')

# Load model and encoders once at startup
try:
    model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODER_PATH)
except Exception as e:
    print(f"Warning: Could not load model or encoders. {e}")
    model = None
    encoders = None

app = FastAPI(title="UEBA API", description="User Entity Behavior Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EventSimulation(BaseModel):
    user_id: str
    timestamp: str
    login_hour: int
    location: str
    ip_address: str
    device_id: str
    download_mb: float
    files_accessed: int
    accessed_department: str

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the UEBA API",
        "endpoints": [
            "GET /alerts",
            "GET /alerts/summary",
            "GET /user/{user_id}",
            "PATCH /alerts/{risk_event_id}/review",
            "POST /simulate-event",
            "GET /health"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/alerts")
def get_alerts():
    conn = get_connection()
    try:
        query = """
        SELECT r.risk_event_id, r.user_id, a.user_name, a.department, r.risk_score, r.reasons, r.flagged_at, r.reviewed
        FROM risk_events r
        JOIN activity_logs a ON r.event_id = a.event_id
        WHERE r.risk_score > 60
        ORDER BY r.risk_score DESC
        """
        df = pd.read_sql_query(query, conn)
        
        alerts = []
        for _, row in df.iterrows():
            alerts.append({
                "risk_event_id": row['risk_event_id'],
                "user_id": row['user_id'],
                "user_name": row['user_name'],
                "department": row['department'],
                "risk_score": row['risk_score'],
                "reasons": str(row['reasons']).split(',') if pd.notnull(row['reasons']) and str(row['reasons']) != "" else [],
                "flagged_at": row['flagged_at'],
                "reviewed": bool(row['reviewed'])
            })
        return alerts
    finally:
        conn.close()

@app.get("/alerts/summary")
def get_alerts_summary():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT risk_score FROM risk_events", conn)
        total_alerts = len(df)
        high_risk = len(df[df['risk_score'] > 80])
        medium_risk = len(df[(df['risk_score'] > 60) & (df['risk_score'] <= 80)])
        
        return {
            "total_alerts": total_alerts,
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "timestamp": datetime.now().isoformat()
        }
    finally:
        conn.close()

@app.get("/user/{user_id}")
def get_user_data(user_id: str):
    conn = get_connection()
    try:
        df_base = pd.read_sql_query(f"SELECT * FROM user_baselines WHERE user_id = '{user_id}'", conn)
        if df_base.empty:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found in baselines.")
        baseline = df_base.iloc[0].to_dict()
        
        df_activity = pd.read_sql_query(f"SELECT * FROM activity_logs WHERE user_id = '{user_id}' ORDER BY timestamp DESC LIMIT 100", conn)
        activity_history = df_activity.to_dict(orient='records')
        
        df_risk = pd.read_sql_query(f"SELECT * FROM risk_events WHERE user_id = '{user_id}' ORDER BY risk_score DESC", conn)
        risk_history = []
        for _, row in df_risk.iterrows():
            r_dict = row.to_dict()
            r_dict['reasons'] = str(r_dict['reasons']).split(',') if pd.notnull(r_dict['reasons']) and r_dict['reasons'] != "" else []
            r_dict['reviewed'] = bool(r_dict['reviewed'])
            risk_history.append(r_dict)
            
        return {
            "baseline": baseline,
            "activity_history": activity_history,
            "risk_history": risk_history
        }
    finally:
        conn.close()

@app.patch("/alerts/{risk_event_id}/review")
def review_alert(risk_event_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE risk_events SET reviewed = 1 WHERE risk_event_id = {risk_event_id}")
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Risk event not found.")
        conn.commit()
        return {"status": "success", "message": f"Alert {risk_event_id} marked as reviewed."}
    finally:
        conn.close()

@app.post("/simulate-event")
def simulate_event(event: EventSimulation):
    if model is None or encoders is None:
        raise HTTPException(status_code=500, detail="Model or encoders not loaded properly.")
        
    conn = get_connection()
    try:
        df_base = pd.read_sql_query(f"SELECT * FROM user_baselines WHERE user_id = '{event.user_id}'", conn)
        if df_base.empty:
            raise HTTPException(status_code=404, detail=f"Baseline not found for user {event.user_id}")
        baseline = df_base.iloc[0].to_dict()
        
        event_dict = event.model_dump()
        
        df_user = pd.read_sql_query(f"SELECT user_name, department FROM activity_logs WHERE user_id = '{event.user_id}' LIMIT 1", conn)
        user_name = df_user.iloc[0]['user_name'] if not df_user.empty else "Unknown"
        department = df_user.iloc[0]['department'] if not df_user.empty else "Unknown"
        
        event_dict['user_name'] = user_name
        event_dict['department'] = department
        event_dict['is_anomaly'] = 0
        
        # Load all past data to get an accurate scaled ML score
        df_logs = pd.read_sql_query("SELECT * FROM activity_logs", conn)
        df_all = pd.concat([df_logs, pd.DataFrame([event_dict])], ignore_index=True)
        
        df_all['department_mismatch'] = (df_all['accessed_department'] != df_all['department']).astype(int)
        
        # Safely handle unseen labels for transform across all historical data
        unseen_locs = set(df_all['location']) - set(encoders['location'].classes_)
        if unseen_locs:
            encoders['location'].classes_ = np.append(encoders['location'].classes_, list(unseen_locs))
            
        unseen_devs = set(df_all['device_id']) - set(encoders['device'].classes_)
        if unseen_devs:
            encoders['device'].classes_ = np.append(encoders['device'].classes_, list(unseen_devs))
            
        df_all['location_encoded'] = encoders['location'].transform(df_all['location'])
        df_all['device_encoded'] = encoders['device'].transform(df_all['device_id'])
        
        feature_cols = ['download_mb', 'login_hour', 'location_encoded', 'device_encoded', 'department_mismatch', 'files_accessed']
        
        scores_all = model.decision_function(df_all[feature_cols])
        scaler = MinMaxScaler(feature_range=(0, 100))
        scaled_scores = scaler.fit_transform((-scores_all).reshape(-1, 1)).flatten()
        
        ml_score = scaled_scores[-1]
        event_dict['ml_anomaly_score'] = ml_score
        
        final_score, reasons = calculate_final_risk_score(event_dict, baseline, ml_score)
        
        # Insert event into activity_logs
        cursor = conn.cursor()
        insert_log_sql = '''
            INSERT INTO activity_logs (
                user_id, user_name, department, timestamp, login_hour, 
                location, ip_address, device_id, download_mb, files_accessed, 
                accessed_department, is_anomaly
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cursor.execute(insert_log_sql, (
            event_dict['user_id'], event_dict['user_name'], event_dict['department'], 
            event_dict['timestamp'], event_dict['login_hour'], event_dict['location'], 
            event_dict['ip_address'], event_dict['device_id'], event_dict['download_mb'], 
            event_dict['files_accessed'], event_dict['accessed_department'], False
        ))
        new_event_id = cursor.lastrowid
        
        if final_score > 40:
            insert_risk_sql = '''
                INSERT INTO risk_events (event_id, user_id, risk_score, reasons, flagged_at, reviewed)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            cursor.execute(insert_risk_sql, (
                new_event_id, event_dict['user_id'], final_score, ",".join(reasons), datetime.now().isoformat(), False
            ))
            
        conn.commit()
        
        return {
            "status": "success",
            "message": "Event processed.",
            "event_id": new_event_id,
            "ml_anomaly_score": round(ml_score, 2),
            "final_risk_score": final_score,
            "reasons": reasons
        }
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
