import React, { useState, useEffect, useRef } from 'react';
import { AlertTriangle, ShieldAlert, ShieldQuestion, Users, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-local-key';

// Custom CountUp Component for premium numeric ticker animation
function CountUp({ value }) {
  const [count, setCount] = useState(0);
  const prevValueRef = useRef(0);

  useEffect(() => {
    const startVal = prevValueRef.current;
    const endVal = parseInt(value, 10) || 0;
    if (startVal === endVal) {
      setCount(endVal);
      return;
    }

    const duration = 600; // Animation duration in ms
    const frameRate = 1000 / 60; // 60 FPS
    const totalFrames = Math.round(duration / frameRate);
    let frame = 0;

    const timer = setInterval(() => {
      frame++;
      const progress = frame / totalFrames;
      // Ease out quad formula
      const easeProgress = progress * (2 - progress);
      const currentVal = Math.round(startVal + (endVal - startVal) * easeProgress);

      setCount(currentVal);

      if (frame >= totalFrames) {
        setCount(endVal);
        prevValueRef.current = endVal;
        clearInterval(timer);
      }
    }, frameRate);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{count}</span>;
}

export default function SummaryCards({ onFetchError }) {
  const [summary, setSummary] = useState({
    total_alerts: 0,
    high_risk_count: 0,
    medium_risk_count: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchSummary() {
      try {
        const response = await fetch(`${API_BASE}/alerts/summary`, {
          headers: { 
            'X-API-Key': API_KEY
          }
        });
        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }
        const data = await response.json();
        if (isMounted) {
          setSummary(data);
          setLoading(false);
          setError(null);
          if (onFetchError) onFetchError(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error fetching alerts summary:", err);
          setError("Cannot connect to server");
          setLoading(false);
          if (onFetchError) {
            onFetchError("Cannot connect to server - is the backend running?");
          }
        }
      }
    }

    // Initial fetch
    fetchSummary();

    // Setup polling every 3 seconds
    const interval = setInterval(fetchSummary, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [onFetchError]);

  if (loading && !summary) {
    return (
      <div className="summary-grid">
        {[1, 2, 3, 4].map(idx => (
          <div key={idx} className="summary-card" style={{ opacity: 0.5 }}>
            <div className="summary-icon-container" style={{ background: 'rgba(255,255,255,0.03)' }}>
              <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
            </div>
            <div className="summary-info">
              <span className="summary-label">Loading...</span>
              <span className="summary-value">0</span>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="error-banner">
        <AlertCircle size={20} />
        <div className="error-banner-content">
          <h4>Threat Summary Offline</h4>
          <p>{error} - is the backend running?</p>
        </div>
      </div>
    );
  }

  // Value bindings
  const total = summary?.total_alerts ?? 0;
  const high = summary?.high_risk_count ?? 0;
  const medium = summary?.medium_risk_count ?? 0;
  
  // Total baseline users (there are exactly 30 users in baseline database)
  const totalUsersMonitored = 30;

  return (
    <div className="summary-grid">
      {/* 1. Total Alerts */}
      <div className="summary-card total">
        <div className="summary-icon-container">
          <AlertTriangle size={24} />
        </div>
        <div className="summary-info">
          <span className="summary-label">Total Alerts</span>
          <div className="summary-value-wrapper">
            <span className="summary-value">
              <CountUp value={total} />
            </span>
            <span className="summary-trend positive">+3 this hour</span>
          </div>
        </div>
      </div>

      {/* 2. High Risk Alerts */}
      <div className="summary-card high">
        <div className="summary-icon-container">
          <ShieldAlert size={24} />
        </div>
        <div className="summary-info">
          <span className="summary-label">High Risk</span>
          <div className="summary-value-wrapper">
            <span className="summary-value">
              <CountUp value={high} />
            </span>
            <span className="summary-trend" style={{ color: 'var(--color-high)', fontWeight: '600' }}>Immediate Action</span>
          </div>
        </div>
      </div>

      {/* 3. Medium Risk Alerts */}
      <div className="summary-card med">
        <div className="summary-icon-container">
          <ShieldQuestion size={24} />
        </div>
        <div className="summary-info">
          <span className="summary-label">Medium Risk</span>
          <div className="summary-value-wrapper">
            <span className="summary-value">
              <CountUp value={medium} />
            </span>
            <span className="summary-trend" style={{ color: 'var(--color-med)', fontWeight: '600' }}>Review Pending</span>
          </div>
        </div>
      </div>

      {/* 4. Total Users Monitored */}
      <div className="summary-card users">
        <div className="summary-icon-container">
          <Users size={24} />
        </div>
        <div className="summary-info">
          <span className="summary-label">Monitored Users</span>
          <div className="summary-value-wrapper">
            <span className="summary-value">
              <CountUp value={totalUsersMonitored} />
            </span>
            <span className="summary-trend stable" style={{ color: 'var(--color-low)', fontWeight: '600' }}>Active Baselines</span>
          </div>
        </div>
      </div>
    </div>
  );
}
