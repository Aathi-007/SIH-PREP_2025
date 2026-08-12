import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, ArrowUpDown, ChevronLeft, ChevronRight, 
  RefreshCw, AlertCircle, ShieldAlert, Filter 
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function AlertsTable({ alerts, loading, error, onRowClick }) {
  // Search and Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('All');

  // Sorting States
  const [sortField, setSortField] = useState('risk_score');
  const [sortDirection, setSortDirection] = useState('desc');

  // Pagination States
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Local state for checking "current time" to compute "NEW" badges dynamically
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    // Keep local clock updated every second for the "NEW" badge comparison
    const timeTimer = setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => clearInterval(timeTimer);
  }, []);

  // Helper: check if threat flagged in last 10 seconds
  const isNewAlert = (flaggedAtStr) => {
    if (!flaggedAtStr) return false;
    const flaggedDate = new Date(flaggedAtStr);
    const diffMs = now.getTime() - flaggedDate.getTime();
    return diffMs >= 0 && diffMs <= 10000; // 10 seconds threshold
  };

  // Helper to format reasons
  const formatReason = (reason) => {
    if (!reason) return '';
    return reason
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Helper to format timestamps
  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    try {
      const date = new Date(timeStr);
      return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch (e) {
      return timeStr;
    }
  };

  // Helper: Department styling class mapper
  const getDeptClass = (dept) => {
    if (!dept) return 'default';
    const d = dept.toLowerCase();
    if (d.includes('hr')) return 'hr';
    if (d.includes('fin')) return 'finance';
    if (d.includes('eng')) return 'engineering';
    if (d.includes('sale')) return 'sales';
    if (d.includes('it')) return 'it';
    return 'default';
  };

  // Helper: Get department display abbreviation
  const getDeptAbbrev = (dept) => {
    if (!dept) return '??';
    if (dept.toUpperCase().includes('HR')) return 'HR';
    if (dept.toUpperCase().includes('IT')) return 'IT';
    return dept.substring(0, 2).toUpperCase();
  };

  // Sorting handler
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc'); // Default to descending on new field
    }
  };

  // Filter alerts by search query and department dropdown
  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = 
      alert.user_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
      alert.user_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      alert.department.toLowerCase().includes(searchQuery.toLowerCase());
      
    const matchesDept = selectedDept === 'All' || alert.department === selectedDept;
    
    return matchesSearch && matchesDept;
  });

  // Sort filtered alerts
  const sortedAlerts = [...filteredAlerts].sort((a, b) => {
    let comparison = 0;
    if (sortField === 'risk_score') {
      comparison = a.risk_score - b.risk_score;
    } else if (sortField === 'flagged_at') {
      comparison = new Date(a.flagged_at) - new Date(b.flagged_at);
    } else if (sortField === 'user_name') {
      comparison = a.user_name.localeCompare(b.user_name);
    }
    return sortDirection === 'asc' ? comparison : -comparison;
  });

  // Pagination bounds
  const totalItems = sortedAlerts.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedAlerts = sortedAlerts.slice(startIndex, startIndex + itemsPerPage);

  // Auto-reset page if query filters reduce matches below index bounds
  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [filteredAlerts.length, totalPages, currentPage]);

  // Extract unique departments for dropdown
  const departments = ['All', ...new Set(alerts.map(a => a.department))];

  if (loading && alerts.length === 0) {
    return (
      <div className="dashboard-card">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading threat logs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-card">
      <div className="dashboard-card-header">
        <h2>
          <ShieldAlert size={18} style={{ color: 'var(--color-high)' }} />
          Threat Detection Register
        </h2>
        <span style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignState: 'center', gap: '6px' }}>
          <RefreshCw size={12} className="spin-slow" /> Polling Real-Time Logins
        </span>
      </div>

      {/* Filter and Search Bar Toolbar */}
      <div className="table-toolbar">
        <div className="search-input-wrapper">
          <Search size={16} />
          <input 
            type="text" 
            placeholder="Search user, ID, department..." 
            className="search-input"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
          />
        </div>

        <div className="filter-actions">
          <Filter size={16} style={{ color: '#64748b' }} />
          <select 
            className="filter-select"
            value={selectedDept}
            onChange={(e) => {
              setSelectedDept(e.target.value);
              setCurrentPage(1);
            }}
          >
            {departments.map((dept, idx) => (
              <option key={idx} value={dept}>
                {dept === 'All' ? 'All Departments' : dept}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && alerts.length === 0 ? (
        <div className="no-data">
          <AlertCircle size={24} style={{ color: 'var(--color-high)', marginBottom: '8px' }} />
          <p>{error} - is the backend running?</p>
        </div>
      ) : sortedAlerts.length === 0 ? (
        <div className="no-data">
          <p>No threat entries match your filter criteria.</p>
        </div>
      ) : (
        <>
          <div className="alerts-table-container">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('user_name')}>
                    <div className="th-content">
                      User / Profile <ArrowUpDown size={12} />
                    </div>
                  </th>
                  <th>Department</th>
                  <th onClick={() => handleSort('risk_score')}>
                    <div className="th-content">
                      Threat Index <ArrowUpDown size={12} />
                    </div>
                  </th>
                  <th>Anomaly Flags</th>
                  <th onClick={() => handleSort('flagged_at')}>
                    <div className="th-content">
                      Timestamp <ArrowUpDown size={12} />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <AnimatePresence mode="popLayout">
                  {paginatedAlerts.map((alert) => {
                    const isHigh = alert.risk_score > 80;
                    const isMed = alert.risk_score >= 60 && alert.risk_score <= 80;
                    const scoreClass = isHigh ? 'high' : isMed ? 'med' : 'low';
                    const isNew = isNewAlert(alert.flagged_at);

                    return (
                      <motion.tr 
                        key={alert.risk_event_id} 
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        transition={{ duration: 0.2 }}
                        onClick={() => onRowClick(alert.user_id)}
                        className={isHigh ? 'risk-critical' : isMed ? 'risk-high' : ''}
                      >
                        {/* User Cell with Avatar */}
                        <td>
                          <div className="user-cell-wrapper">
                            <div className={`dept-avatar ${getDeptClass(alert.department)}`}>
                              {getDeptAbbrev(alert.department)}
                            </div>
                            <div className="user-text-info">
                              <span className="user-name-cell">
                                {alert.user_name}
                                {isNew && <span className="new-badge">NEW</span>}
                              </span>
                              <span style={{ fontSize: '11px', color: '#64748b' }}>
                                ID: {alert.user_id}
                              </span>
                            </div>
                          </div>
                        </td>
                        
                        {/* Department */}
                        <td>{alert.department}</td>
                        
                        {/* Threat progress bar */}
                        <td>
                          <div className="score-wrapper">
                            <span className={`score-num ${scoreClass}`}>
                              {alert.risk_score}
                            </span>
                            <div className="score-bar-bg">
                              <div 
                                className={`score-bar-fill ${scoreClass}`} 
                                style={{ width: `${alert.risk_score}%` }}
                              />
                            </div>
                          </div>
                        </td>
                        
                        {/* Anomaly pills */}
                        <td>
                          <div className="reasons-container">
                            {alert.reasons && alert.reasons.length > 0 ? (
                              alert.reasons.map((r, idx) => (
                                <span 
                                  key={idx} 
                                  className={`reason-pill ${r.includes('anomaly') || r.includes('download') ? 'anomaly' : ''}`}
                                >
                                  {formatReason(r)}
                                </span>
                              ))
                            ) : (
                              <span className="reason-pill">Baseline Checked</span>
                            )}
                          </div>
                        </td>
                        
                        {/* Flagged Time */}
                        <td className="timestamp-text">
                          {formatTime(alert.flagged_at)}
                        </td>
                      </motion.tr>
                    );
                  })}
                </AnimatePresence>
              </tbody>
            </table>
          </div>

          {/* Table Pagination */}
          <div className="table-pagination">
            <span className="pagination-info">
              Showing <strong>{startIndex + 1}</strong> to <strong>{Math.min(startIndex + itemsPerPage, totalItems)}</strong> of <strong>{totalItems}</strong> entries
            </span>
            <div className="pagination-controls">
              <button 
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft size={16} /> Prev
              </button>
              <button 
                className="pagination-btn"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
