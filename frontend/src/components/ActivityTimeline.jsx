import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldAlert } from 'lucide-react';

export default function ActivityTimeline({ alerts, onRowClick }) {
  // Sort alerts by flagged_at descending (newest first) and display top 6
  const recentAlerts = [...alerts]
    .sort((a, b) => new Date(b.flagged_at) - new Date(a.flagged_at))
    .slice(0, 6);

  // Helper to format reasons
  const formatReason = (reasons) => {
    if (!reasons || reasons.length === 0) return 'Baseline check';
    return reasons
      .map(r => r.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '))
      .join(', ');
  };

  // Helper to format date
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    try {
      const date = new Date(timeStr);
      return date.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch (e) {
      return timeStr;
    }
  };

  return (
    <div className="dashboard-card timeline-card">
      <div className="dashboard-card-header" style={{ borderBottom: 'none', padding: '0 0 20px 0' }}>
        <h2>
          <Activity size={18} style={{ color: 'var(--color-high)' }} />
          Operations Feed
        </h2>
      </div>

      <div className="timeline-list">
        {recentAlerts.length === 0 ? (
          <div style={{ padding: '20px 0', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
            No recent anomalies.
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {recentAlerts.map((alert) => {
              const isCrit = alert.risk_score > 80;
              const dotClass = isCrit ? 'critical' : 'high';
              const scoreClass = isCrit ? 'critical' : 'high';

              return (
                <motion.div
                  key={alert.risk_event_id}
                  layout
                  initial={{ opacity: 0, y: -20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="timeline-item"
                  onClick={() => onRowClick(alert.user_id)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Glowing dot for timeline marker */}
                  <div className={`timeline-dot ${dotClass}`} />
                  
                  <div className="timeline-content">
                    <div className="timeline-meta">
                      <span className="timeline-user">{alert.user_name}</span>
                      <span className={`timeline-score ${scoreClass}`}>
                        {alert.risk_score}
                      </span>
                    </div>
                    <div className="timeline-reasons" title={formatReason(alert.reasons)}>
                      {formatReason(alert.reasons)}
                    </div>
                    <span className="timeline-time">
                      {formatTime(alert.flagged_at)}
                    </span>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
