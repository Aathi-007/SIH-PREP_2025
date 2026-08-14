import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from collections import deque
import time
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import joblib
from sklearn.preprocessing import MinMaxScaler
import uvicorn

from database import get_connection
from risk_scoring import calculate_rule_based_score, calculate_final_risk_score
from auth import verify_password, create_access_token, verify_token

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

cors_origins_str = os.environ.get("CORS_ORIGINS")
if cors_origins_str:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
else:
    cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store the last 1000 requests to track real-time traffic
api_traffic_log = deque(maxlen=2000)

# Pre-seed with some dummy background noise for the last 15 minutes
import random
now_ts = time.time()
for i in range(15 * 60): # 15 minutes of seconds
    if random.random() > 0.3: # 70% chance of a GET request each second
        api_traffic_log.append({
            "timestamp": now_ts - i,
            "method": "GET",
            "is_abnormal": random.random() < 0.02
        })
    if random.random() > 0.95: # 5% chance of a POST request each second
        api_traffic_log.append({
            "timestamp": now_ts - i,
            "method": "POST",
            "is_abnormal": random.random() < 0.15
        })

@app.middleware("http")
async def track_api_traffic(request: Request, call_next):
    # Initialize state
    request.state.is_abnormal = False
    
    response = await call_next(request)
    
    is_abnormal = getattr(request.state, "is_abnormal", False) or response.status_code >= 400
    
    if request.method in ("GET", "POST"):
        api_traffic_log.append({
            "timestamp": time.time(),
            "method": request.method,
            "is_abnormal": is_abnormal
        })
    return response

API_KEY = os.environ.get("UEBA_API_KEY", "dev-local-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security = HTTPBearer()

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=401, detail="Invalid or missing API Key")


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

class AccessRequest(BaseModel):
    resource_id: str
    user_id: str = "U001"
    department: str = "Engineering"
    username: str = "test.user"

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(request: LoginRequest):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, password_hash, role, department FROM users WHERE username = ?", 
            (request.username.strip(),)
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        user_id, username, password_hash, role, department = user
        if not verify_password(request.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        token = create_access_token(data={
            "sub": username, 
            "user_id": user_id, 
            "role": role, 
            "department": department
        })
        return {"access_token": token, "token_type": "bearer"}
    finally:
        conn.close()

@app.post("/access-request")
def access_request(request: AccessRequest, http_request: Request, api_key: str = Depends(get_api_key)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Check if resource exists
        cursor.execute("SELECT owning_department FROM resources WHERE resource_id = ?", (request.resource_id,))
        resource = cursor.fetchone()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")
            
        resource_dept = resource[0]
        user_dept = request.department
        user_id = request.user_id
        user_name = request.username
        timestamp = datetime.now().isoformat()
        
        if resource_dept == user_dept:
            # Allow access and log normal activity
            cursor.execute('''
                INSERT INTO activity_logs (
                    user_id, user_name, department, timestamp, login_hour, 
                    location, ip_address, device_id, download_mb, files_accessed, 
                    accessed_department, is_anomaly
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, user_name, user_dept, timestamp, datetime.now().hour,
                "Unknown", "0.0.0.0", "Unknown", 0.0, 1, resource_dept, False
            ))
            conn.commit()
            return {"allowed": True}
        else:
            # Deny access: 1. log activity as anomaly
            cursor.execute('''
                INSERT INTO activity_logs (
                    user_id, user_name, department, timestamp, login_hour, 
                    location, ip_address, device_id, download_mb, files_accessed, 
                    accessed_department, is_anomaly
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, user_name, user_dept, timestamp, datetime.now().hour,
                "Unknown", "0.0.0.0", "Unknown", 0.0, 1, resource_dept, True
            ))
            new_event_id = cursor.lastrowid
            
            # 2. Log access violation
            cursor.execute('''
                INSERT INTO access_violations (
                    user_id, resource_id, requester_department, resource_department, attempted_at
                ) VALUES (?, ?, ?, ?, ?)
            ''', (user_id, request.resource_id, user_dept, resource_dept, timestamp))
            
            # 3. Create risk event
            cursor.execute('''
                INSERT INTO risk_events (event_id, user_id, risk_score, reasons, flagged_at, reviewed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                new_event_id, user_id, 90, "unauthorized_cross_department_access", timestamp, False
            ))
            
            http_request.state.is_abnormal = True
            conn.commit()
            return JSONResponse(status_code=403, content={"allowed": False})
            
    finally:
        conn.close()

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
            "POST /login",
            "POST /access-request",
            "GET /health"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/alerts")
def get_alerts(api_key: str = Depends(get_api_key)):
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
def get_alerts_summary(api_key: str = Depends(get_api_key)):
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

@app.get("/analytics/daily-risk")
def get_daily_risk(api_key: str = Depends(get_api_key)):
    conn = get_connection()
    try:
        # Get the average risk score per user per day for the last 30 days
        query = """
        SELECT r.user_id, u.username as user_name, date(r.flagged_at) as date, AVG(r.risk_score) as avg_score
        FROM risk_events r
        JOIN users u ON r.user_id = u.user_id
        WHERE date(r.flagged_at) >= date('now', '-30 days')
        GROUP BY r.user_id, date(r.flagged_at)
        """
        df = pd.read_sql_query(query, conn)
        return df.to_dict(orient="records")
    finally:
        conn.close()
@app.get("/analytics/company-behavior-trend")
def get_company_behavior_trend(api_key: str = Depends(get_api_key)):
    from datetime import timedelta
    now = datetime.now()
    
    # Create buckets for the last 15 minutes, minute by minute
    buckets = {}
    for i in range(15):
        t = now - timedelta(minutes=i)
        buckets[t.strftime("%H:%M")] = {
            "get_normal": 0,
            "get_abnormal": 0,
            "post_normal": 0,
            "post_abnormal": 0
        }
        
    for log in api_traffic_log:
        log_time = datetime.fromtimestamp(log["timestamp"])
        time_key = log_time.strftime("%H:%M")
        if time_key in buckets:
            method = log["method"]
            is_abnormal = log.get("is_abnormal", False)
            
            if method == "GET":
                if is_abnormal:
                    buckets[time_key]["get_abnormal"] += 1
                else:
                    buckets[time_key]["get_normal"] += 1
            elif method == "POST":
                if is_abnormal:
                    buckets[time_key]["post_abnormal"] += 1
                else:
                    buckets[time_key]["post_normal"] += 1
                
    # Format and sort results
    res = []
    for k in sorted(buckets.keys()):
        res.append({
            "displayDate": k,
            "get_normal": buckets[k]["get_normal"],
            "get_abnormal": buckets[k]["get_abnormal"],
            "post_normal": buckets[k]["post_normal"],
            "post_abnormal": buckets[k]["post_abnormal"]
        })
    return res

@app.get("/users")
def get_users(api_key: str = Depends(get_api_key)):
    conn = get_connection()
    try:
        query = """
        SELECT u.user_id, u.username, u.department, COALESCE(MAX(r.risk_score), 0) as max_risk
        FROM users u
        LEFT JOIN risk_events r ON u.user_id = r.user_id AND r.flagged_at >= date('now', '-7 days')
        GROUP BY u.user_id
        ORDER BY max_risk DESC, u.username ASC
        """
        df = pd.read_sql_query(query, conn)
        return df.to_dict(orient="records")
    finally:
        conn.close()

@app.get("/user/{user_id}")
def get_user_data(user_id: str, api_key: str = Depends(get_api_key)):
    conn = get_connection()
    try:
        df_base = pd.read_sql_query("SELECT * FROM user_baselines WHERE user_id = ?", conn, params=(user_id,))
        if df_base.empty:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found in baselines.")
        baseline = df_base.iloc[0].to_dict()
        
        df_activity = pd.read_sql_query("SELECT * FROM activity_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 100", conn, params=(user_id,))
        activity_history = df_activity.to_dict(orient='records')
        
        df_risk = pd.read_sql_query("SELECT * FROM risk_events WHERE user_id = ? ORDER BY risk_score DESC", conn, params=(user_id,))
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
def review_alert(risk_event_id: int, api_key: str = Depends(get_api_key)):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE risk_events SET reviewed = 1 WHERE risk_event_id = ?", (risk_event_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Risk event not found.")
        conn.commit()
        return {"status": "success", "message": f"Alert {risk_event_id} marked as reviewed."}
    finally:
        conn.close()

@app.post("/simulate-event")
def simulate_event(event: EventSimulation, http_request: Request, api_key: str = Depends(get_api_key)):
    if model is None or encoders is None:
        raise HTTPException(status_code=500, detail="Model or encoders not loaded properly.")
        
    conn = get_connection()
    try:
        df_base = pd.read_sql_query("SELECT * FROM user_baselines WHERE user_id = ?", conn, params=(event.user_id,))
        if df_base.empty:
            raise HTTPException(status_code=404, detail=f"Baseline not found for user {event.user_id}")
        baseline = df_base.iloc[0].to_dict()
        
        event_dict = event.model_dump()
        
        df_user = pd.read_sql_query("SELECT user_name, department FROM activity_logs WHERE user_id = ? LIMIT 1", conn, params=(event.user_id,))
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
            encoders['location'].classes_ = np.sort(np.append(encoders['location'].classes_, list(unseen_locs)))
            
        unseen_devs = set(df_all['device_id']) - set(encoders['device'].classes_)
        if unseen_devs:
            encoders['device'].classes_ = np.sort(np.append(encoders['device'].classes_, list(unseen_devs)))
            
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
            http_request.state.is_abnormal = True
            
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
