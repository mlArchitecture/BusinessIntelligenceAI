import React, { useState, useContext } from 'react';
import AuthContext from '../../store/auth-context';
import api from '../../utils/api';
import RCAPanel from './RCAPanel';

const Dashboard = () => {
  const authCtx = useContext(AuthContext);
  const [targetKpi, setTargetKpi] = useState('total_revenue');
  const [analysisDate, setAnalysisDate] = useState('');
  const [result, setResult] = useState({ narrative: '', evidence_json: '' });
  const [error, setError] = useState(null);

  const managerKpis = ['total_revenue', 'conversion_rate', 'aov', 'return_rate'];
  const analystKpis = [...managerKpis, 'cac', 'total_orders', 'total_sessions', 'daily_ad_spend'];
  
  const availableKpis = authCtx.persona === 'manager' ? managerKpis : analystKpis;

  const analyzeHandler = async () => {
    try {
      setError(null);
      const response = await api.post('/analyze-variance', {
        target_kpi: targetKpi,
        analysis_date: analysisDate
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed');
    }
  };

  return (
    <div className="min-h-screen p-8 bg-gray-100">
      <div className="flex justify-between mb-8">
        <h1 className="text-3xl font-bold">BI RCA Engine</h1>
        <button onClick={authCtx.logout} className="px-4 py-2 text-white bg-red-500 rounded">Logout</button>
      </div>

      <div className="flex gap-4 p-6 bg-white rounded shadow-md">
        <select 
          className="p-2 border rounded"
          value={targetKpi}
          onChange={(e) => setTargetKpi(e.target.value)}
        >
          {availableKpis.map(kpi => <option key={kpi} value={kpi}>{kpi}</option>)}
        </select>
        
        <input 
          type="date" 
          className="p-2 border rounded"
          value={analysisDate}
          onChange={(e) => setAnalysisDate(e.target.value)}
        />
        
        <button 
          onClick={analyzeHandler}
          className="px-6 py-2 text-white bg-blue-600 rounded"
        >
          Execute Pipeline
        </button>
      </div>

      {error && <div className="p-4 mt-6 text-red-700 bg-red-100 rounded">{error}</div>}
      
      <RCAPanel narrative={result.narrative} evidence={result.evidence_json} />
    </div>
  );
};

export default Dashboard;
