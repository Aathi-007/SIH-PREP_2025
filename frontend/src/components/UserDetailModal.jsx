import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, 
  CartesianGrid, Tooltip, ReferenceLine, Label,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar 
} from 'recharts';
import { 
  X, Shield, Activity, BarChart2, Layers, 
  Download, Clock, Laptop, Globe, AlertTriangle 
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-local-key';

export default function UserDetailModal({ userId, onClose, jwt }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!userId || !jwt) return;

    let isMounted = true;
    setLoading(true);

    async function fetchUserData() {
      try {
        const response = await fetch(`${API_BASE}/user/${userId}`, {
          headers: { 
            'X-API-Key': API_KEY,
            'Authorization': `Bearer ${jwt}`
          }
        });
        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }
        const jsonData = await response.json();
        
        if (isMounted) {
          setData(jsonData);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error fetching user detail:", err);
          setError("Failed to load user profile");
          setLoading(false);
        }
      }
    }

    fetchUserData();

    return () => {
      isMounted = false;
    };
  }, [userId, jwt]);

  if (!userId) return null;

  // Helper to format reasons
  const formatReason = (reason) => {
    if (!reason) return '';
    return reason
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Helper: compute radar chart values based on real risk history reason contribution
  const getRadarData = (riskHistory) => {
    const categories = {
      'Download Vol': 0,
      'Location': 0,
      'Login Hour': 0,
      'Device': 0,
      'Dept Access': 0
    };

    if (!riskHistory || riskHistory.length === 0) {
      return Object.keys(categories).map(subject => ({ subject, score: 20 }));
    }

    riskHistory.forEach(event => {
      const score = event.risk_score || 60;
      const reasons = event.reasons || [];
      
      reasons.forEach(reason => {
        const r = reason.toLowerCase();
        if (r.includes('download')) {
          categories['Download Vol'] = Math.max(categories['Download Vol'], score);
        }
        if (r.includes('location')) {
          categories['Location'] = Math.max(categories['Location'], score);
        }
        if (r.includes('hour') || r.includes('time')) {
          categories['Login Hour'] = Math.max(categories['Login Hour'], score);
        }
        if (r.includes('device')) {
          categories['Device'] = Math.max(categories['Device'], score);
        }
        if (r.includes('department') || r.includes('mismatch')) {
          categories['Dept Access'] = Math.max(categories['Dept Access'], score);
        }
      });
    });

    // Provide default fallback value of 15 for visual appeal on clean categories
    return Object.keys(categories).map(subject => ({
      subject,
      score: categories[subject] === 0 ? 15 : categories[subject]
    }));
  };

  // Format activity history for the Area Chart (chronological sorting)
  const chartData = data?.activity_history 
    ? [...data.activity_history].reverse().map(act => ({
        ...act,
        shortTime: new Date(act.timestamp).toLocaleTimeString(undefined, { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
        download: act.download_mb
      }))
    : [];

  const baseline = data?.baseline;
  const riskHistory = data?.risk_history || [];

  // Determine highest threat index to render header banner badge
  const maxRiskScore = riskHistory.length > 0 
    ? Math.max(...riskHistory.map(h => h.risk_score)) 
    : 0;

  const isCritical = maxRiskScore > 80;
  const isHigh = maxRiskScore >= 60 && maxRiskScore <= 80;
  const threatLabel = isCritical ? 'CRITICAL THREAT' : isHigh ? 'HIGH RISK PROFILE' : 'MONITORED';
  const badgeColor = isCritical ? 'var(--color-high)' : isHigh ? 'var(--color-med)' : 'var(--color-low)';
  const badgeBg = isCritical ? 'var(--color-high-bg)' : isHigh ? 'var(--color-med-bg)' : 'var(--color-low-bg)';

  return (
    <div className="modal-overlay" onClick={onClose}>
      {/* Framer motion wrapper for modal scale in */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className="modal-container" 
        onClick={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-wrapper">
            <Shield size={24} style={{ color: badgeColor }} />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3>Forensic Investigation</h3>
                <span 
                  style={{
                    fontSize: '10px',
                    fontWeight: '800',
                    color: badgeColor,
                    background: badgeBg,
                    border: `1px solid ${badgeColor}30`,
                    padding: '2px 8px',
                    borderRadius: '4px',
                    letterSpacing: '0.5px'
                  }}
                >
                  {threatLabel}
                </span>
              </div>
              <p className="modal-header-subtitle">
                Correlated metadata analysis for User: <strong>{data?.activity_history?.[0]?.user_name || userId}</strong> (ID: {userId})
              </p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        {loading ? (
          <div style={{ height: '350px' }} className="loading-container">
            <div className="spinner"></div>
            <p>Constructing forensics timelines...</p>
          </div>
        ) : error ? (
          <div style={{ height: '200px', padding: '40px' }} className="no-data">
            <p style={{ color: 'var(--color-high)' }}>{error}</p>
            <button onClick={onClose} className="pagination-btn" style={{ margin: '16px auto 0 auto' }}>
              Dismiss Profile
            </button>
          </div>
        ) : (
          <div className="modal-body">
            
            {/* Top Grid: Baseline Metrics & Radar Threat Chart */}
            <div className="modal-grid-top">
              
              {/* Left Side: Dynamic Radar Chart */}
              <div className="radar-section">
                <h4>
                  <AlertTriangle size={14} style={{ color: 'var(--color-high)' }} />
                  Behavioral Anomalies Vector
                </h4>
                <div className="radar-chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="75%" data={getRadarData(riskHistory)}>
                      <PolarGrid stroke="rgba(255, 255, 255, 0.05)" />
                      <PolarAngleAxis 
                        dataKey="subject" 
                        stroke="#94a3b8" 
                        fontSize={10} 
                      />
                      <PolarRadiusAxis 
                        angle={30} 
                        domain={[0, 100]} 
                        stroke="rgba(255, 255, 255, 0.1)" 
                        fontSize={8} 
                      />
                      <Radar
                        name="Anomaly Severity"
                        dataKey="score"
                        stroke={badgeColor}
                        fill={badgeColor}
                        fillOpacity={0.25}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Right Side: Operational Baseline List */}
              <div className="baseline-section">
                <h4>
                  <Layers size={14} style={{ color: 'var(--color-info)' }} />
                  Operational Baselines
                </h4>
                <div className="baseline-list-box">
                  <div className="baseline-row-item">
                    <div className="baseline-row-left">
                      <Layers size={14} />
                      <span>Home Department</span>
                    </div>
                    <span className="baseline-row-value">{baseline?.usual_department || 'Unknown'}</span>
                  </div>
                  
                  <div className="baseline-row-item">
                    <div className="baseline-row-left">
                      <Download size={14} />
                      <span>Avg Download Limit</span>
                    </div>
                    <span className="baseline-row-value">
                      {baseline?.avg_download_mb != null 
                        ? `${baseline.avg_download_mb.toFixed(1)} MB` 
                        : '0.0 MB'}
                    </span>
                  </div>
                  
                  <div className="baseline-row-item">
                    <div className="baseline-row-left">
                      <Clock size={14} />
                      <span>Usual Work Hours</span>
                    </div>
                    <span className="baseline-row-value">
                      {baseline?.usual_login_hour_start != null && baseline?.usual_login_hour_end != null
                        ? `${String(baseline.usual_login_hour_start).padStart(2, '0')}:00 - ${String(baseline.usual_login_hour_end).padStart(2, '0')}:00`
                        : 'Not logged'}
                    </span>
                  </div>

                  <div className="baseline-row-item">
                    <div className="baseline-row-left">
                      <Laptop size={14} />
                      <span>Known Devices</span>
                    </div>
                    <span className="baseline-row-value" title={baseline?.known_devices}>
                      {baseline?.known_devices || 'None'}
                    </span>
                  </div>

                  <div className="baseline-row-item">
                    <div className="baseline-row-left">
                      <Globe size={14} />
                      <span>Known Locations</span>
                    </div>
                    <span className="baseline-row-value" title={baseline?.known_locations}>
                      {baseline?.known_locations || 'None'}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Middle Section: Download Spikes Area Chart */}
            <div className="chart-section">
              <h4>
                <BarChart2 size={14} style={{ color: 'var(--color-info)' }} />
                Data Transfer Volume vs Baseline Limit
              </h4>
              <div className="chart-container">
                {chartData.length === 0 ? (
                  <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <p style={{ color: '#64748b' }}>No data transfer history.</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={chartData}
                      margin={{ top: 15, right: 10, left: -20, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient id="colorSpike" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                      <XAxis 
                        dataKey="shortTime" 
                        stroke="#64748b" 
                        fontSize={10}
                        tickLine={false}
                      />
                      <YAxis 
                        stroke="#64748b" 
                        fontSize={10} 
                        tickLine={false}
                        unit="MB"
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#0d1222',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '8px',
                          color: '#fff',
                          fontSize: '12px'
                        }}
                        labelFormatter={(label, items) => {
                          if (items[0]?.payload) {
                            return `Logged: ${new Date(items[0].payload.timestamp).toLocaleString()}`;
                          }
                          return label;
                        }}
                      />
                      
                      {/* Red reference line for the user's baseline limit */}
                      {baseline?.avg_download_mb != null && (
                        <ReferenceLine 
                          y={baseline.avg_download_mb} 
                          stroke="#ef4444" 
                          strokeDasharray="4 4"
                          strokeWidth={1.5}
                        >
                          <Label 
                            value="Baseline Limit" 
                            position="top" 
                            fill="#fda4af" 
                            fontSize={10} 
                            offset={5}
                          />
                        </ReferenceLine>
                      )}

                      <Area 
                        type="monotone" 
                        dataKey="download" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorSpike)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            {/* Bottom Section: Historical Anomaly Registry */}
            <div className="history-section">
              <h4>
                <Activity size={14} style={{ color: 'var(--color-high)' }} />
                Anomalous Incident History
              </h4>
              <div className="history-timeline">
                {riskHistory.length === 0 ? (
                  <p style={{ fontSize: '13px', color: '#64748b' }}>
                    No security flags logged.
                  </p>
                ) : (
                  riskHistory.map((item) => {
                    const isCrit = item.risk_score > 80;
                    return (
                      <div key={item.risk_event_id} className="history-item">
                        <div className="history-item-left">
                          <div className="history-item-meta">
                            <span className={`history-item-score ${isCrit ? 'critical' : 'high'}`}>
                              Risk Index: {item.risk_score}
                            </span>
                            <span className="history-item-date">
                              {new Date(item.flagged_at).toLocaleString()}
                            </span>
                          </div>
                          <div className="reasons-container" style={{ marginTop: '4px' }}>
                            {item.reasons && item.reasons.length > 0 ? (
                              item.reasons.map((r, i) => (
                                <span key={i} className="reason-pill anomaly">
                                  {formatReason(r)}
                                </span>
                              ))
                            ) : (
                              <span className="reason-pill">Baseline Check</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

          </div>
        )}
      </motion.div>
    </div>
  );
}
