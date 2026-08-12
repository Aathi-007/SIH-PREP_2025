import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Download, Clock, AlertCircle } from 'lucide-react';
import SummaryCards from './components/SummaryCards';
import AlertsTable from './components/AlertsTable';
import UserDetailModal from './components/UserDetailModal';
import RiskTrendChart from './components/RiskTrendChart';
import ActivityTimeline from './components/ActivityTimeline';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState(null);
  
  // State for live clock in header
  const [currentTime, setCurrentTime] = useState(new Date());

  // Polling Alerts Data in App.jsx to synchronize all charts and grids
  useEffect(() => {
    let isMounted = true;

    async function fetchAlerts() {
      try {
        const response = await fetch(`${API_BASE}/alerts`);
        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }
        const data = await response.json();
        
        if (isMounted) {
          setAlerts(data);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error polling alerts in App:", err);
          setError("Cannot connect to server - is the backend running?");
          setLoading(false);
        }
      }
    }

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 3000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Update live clock every second
  useEffect(() => {
    const clockTimer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(clockTimer);
  }, []);

  // Report Export Feature: Downloads active alerts array as a JSON file
  const handleExportReport = () => {
    if (alerts.length === 0) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(alerts, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `UEBA_SOC_Report_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="dashboard-container"
    >
      {/* 1. Header with Title, Subtitle, Date/Time, Status, and Export Report */}
      <header className="dashboard-header">
        <div className="header-titles">
          <h1>
            <ShieldAlert size={28} style={{ color: 'var(--color-high)' }} />
            UEBA Insider Threat Console
          </h1>
          <p>Real-time User Entity Behavior Analytics & SOC Monitoring Command</p>
        </div>
        
        <div className="header-actions">
          <div className="live-clock">
            <Clock size={14} />
            <span>
              {currentTime.toLocaleDateString(undefined, { 
                weekday: 'short', 
                month: 'short', 
                day: 'numeric' 
              })}
              {' '}
              {currentTime.toLocaleTimeString()}
            </span>
          </div>

          <div className="live-indicator">
            <div className="live-dot"></div>
            <span>Live Feed</span>
          </div>

          <button 
            className="export-btn" 
            onClick={handleExportReport}
            disabled={alerts.length === 0}
            title="Download JSON threat summary"
          >
            <Download size={14} />
            Export Report
          </button>
        </div>
      </header>

      {/* 2. Global Server Connection Error Banner */}
      {error && (
        <div className="error-banner">
          <AlertCircle size={20} />
          <div className="error-banner-content">
            <h4>SOC Console Offline</h4>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* 3. Threat Metrics Summary Card Grid */}
      <SummaryCards onFetchError={setError} />

      {/* 4. Two-Column SOC Dashboard Grid */}
      <div className="dashboard-grid">
        
        {/* Left / Primary Column (Trend Line and Core Alerts Table) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <RiskTrendChart alerts={alerts} />
          
          <AlertsTable 
            alerts={alerts}
            loading={loading}
            error={error}
            onRowClick={setSelectedUserId} 
          />
        </div>

        {/* Right / Sidebar Column (Operations timeline feed) */}
        <div>
          <ActivityTimeline 
            alerts={alerts} 
            onRowClick={setSelectedUserId}
          />
        </div>
      </div>

      {/* 5. User Forensic Modal (Drill-Down Investigation) */}
      <AnimatePresence>
        {selectedUserId && (
          <UserDetailModal 
            userId={selectedUserId} 
            onClose={() => setSelectedUserId(null)} 
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
