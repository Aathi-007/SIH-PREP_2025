import React, { useState, useEffect } from 'react';
import { Users, Search, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-local-key';

export default function UserDirectory({ onUserClick }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    let isMounted = true;
    
    async function fetchUsers() {
      try {
        const response = await fetch(`${API_BASE}/users`, {
          headers: { 'X-API-Key': API_KEY }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch users');
        }
        
        const data = await response.json();
        if (isMounted) {
          setUsers(data);
          setLoading(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError('Cannot load user directory');
          setLoading(false);
        }
      }
    }

    fetchUsers();
    // Poll every 5 seconds to get updated risk scores
    const interval = setInterval(fetchUsers, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const filteredUsers = users.filter(u => 
    u.username.toLowerCase().includes(searchTerm.toLowerCase()) || 
    u.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="dashboard-card" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxHeight: '450px' }}>
      <div style={{ padding: '16px 20px 16px 20px' }}>
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
          <Search size={14} style={{ position: 'absolute', left: '12px', color: '#64748b' }} />
          <input 
            type="text" 
            placeholder="Search users..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ 
              width: '100%', 
              padding: '10px 10px 10px 32px', 
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              background: 'rgba(255, 255, 255, 0.03)',
              color: '#fff',
              outline: 'none',
              fontSize: '13px'
            }}
          />
        </div>
      </div>

      <div style={{ overflowY: 'auto', flex: 1, padding: '0 20px 20px 20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '13px' }}>Loading directory...</div>
        ) : error ? (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--color-high)', fontSize: '13px' }}>{error}</div>
        ) : filteredUsers.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '13px' }}>No users found.</div>
        ) : (
          filteredUsers.map(user => {
            const isHighRisk = user.max_risk >= 80;
            const isMediumRisk = user.max_risk >= 50 && user.max_risk < 80;
            
            return (
              <div 
                key={user.user_id}
                onClick={() => onUserClick && onUserClick(user.user_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'background 0.2s ease, border-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: isHighRisk ? 'rgba(244, 63, 94, 0.2)' : isMediumRisk ? 'rgba(234, 179, 8, 0.2)' : 'rgba(34, 197, 94, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: isHighRisk ? 'var(--color-high)' : isMediumRisk ? 'var(--color-medium)' : 'var(--color-low)'
                  }}>
                    {isHighRisk ? <AlertTriangle size={14} /> : isMediumRisk ? <Activity size={14} /> : <ShieldCheck size={14} />}
                  </div>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: '600', color: '#e2e8f0', marginBottom: '2px' }}>
                      {user.username}
                    </div>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                      {user.department}
                    </div>
                  </div>
                </div>
                
                {user.max_risk > 0 && (
                  <div style={{ 
                    fontSize: '11px', 
                    fontWeight: '700', 
                    color: isHighRisk ? 'var(--color-high)' : isMediumRisk ? 'var(--color-medium)' : 'var(--color-low)'
                  }}>
                    {user.max_risk.toFixed(0)}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
