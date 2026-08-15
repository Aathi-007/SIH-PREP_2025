import React, { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-local-key';

export default function BehaviorHeatmap({ onCellClick }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchHeatmap() {
      try {
        const response = await fetch(`${API_BASE}/analytics/daily-risk`, {
          headers: { 
            'X-API-Key': API_KEY
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch daily risk data');
        }
        
        const jsonData = await response.json();
        
        if (isMounted) {
          setData(jsonData);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Error fetching heatmap data:", err);
          setError("Failed to load behavior heatmap");
          setLoading(false);
        }
      }
    }

    fetchHeatmap();
    
    // Poll every 10 seconds
    const interval = setInterval(fetchHeatmap, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Generate an array of the last 30 days formatted as 'YYYY-MM-DD'
  const generateLast30Days = () => {
    const dates = [];
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const isoStr = d.toISOString().split('T')[0];
      dates.push(isoStr);
    }
    return dates;
  };

  const days = generateLast30Days();

  // Process data into a matrix: { "username": { "YYYY-MM-DD": avg_score } }
  const userMap = {};
  const userIdMap = {};
  
  data.forEach(row => {
    const { user_id, user_name, date, avg_score } = row;
    if (!userMap[user_name]) {
      userMap[user_name] = {};
      userIdMap[user_name] = user_id;
    }
    userMap[user_name][date] = avg_score;
  });

  const getCellColor = (score) => {
    if (score === undefined || score === null) return 'rgba(255, 255, 255, 0.03)';
    
    // Scale from green (120 hue) to red (0 hue)
    // score 0 -> 120 hue
    // score 100 -> 0 hue
    const clampedScore = Math.max(0, Math.min(100, score));
    const hue = 120 - (clampedScore * 1.2);
    return `hsl(${hue}, 70%, 45%)`;
  };

  if (loading && data.length === 0) {
    return (
      <div className="dashboard-card" style={{ padding: '40px', textAlign: 'center' }}>
        <p style={{ color: '#94a3b8' }}>Loading behavior heatmap...</p>
      </div>
    );
  }

  const usernames = Object.keys(userMap).sort();

  return (
    <div className="dashboard-card" style={{ marginBottom: '24px' }}>
      <div className="dashboard-card-header">
        <h2>
          <Activity size={20} style={{ color: 'var(--color-info)' }} />
          Team Behavior Overview
        </h2>
      </div>
      
      {error ? (
        <div style={{ padding: '24px', color: '#fda4af' }}>{error}</div>
      ) : (
        <div className="heatmap-container">
          <div className="heatmap-grid">
            {usernames.length === 0 ? (
              <p style={{ color: '#94a3b8', padding: '16px' }}>No risk events recorded in the last 30 days.</p>
            ) : (
              usernames.map(username => (
                <div key={username} className="heatmap-row">
                  <div className="heatmap-user-label" title={username}>
                    {username}
                  </div>
                  <div className="heatmap-cells-wrapper">
                    {days.map(day => {
                      const score = userMap[username][day];
                      return (
                        <div 
                          key={`${username}-${day}`} 
                          className="heatmap-cell"
                          style={{ backgroundColor: getCellColor(score) }}
                          title={`${username} | ${day} | Score: ${score !== undefined ? score.toFixed(1) : 'None'}`}
                          onClick={() => onCellClick(userIdMap[username])}
                        />
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
          
          <div className="heatmap-legend">
            <div className="legend-item">
              <div className="legend-color" style={{ background: 'rgba(255, 255, 255, 0.03)' }}></div>
              <span>No Activity</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ background: 'hsl(120, 70%, 45%)' }}></div>
              <span>Low Risk</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ background: 'hsl(60, 70%, 45%)' }}></div>
              <span>Medium Risk</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ background: 'hsl(0, 70%, 45%)' }}></div>
              <span>High Risk</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
