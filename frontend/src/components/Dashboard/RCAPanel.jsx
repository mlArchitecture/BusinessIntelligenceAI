import React from 'react';
import ReactMarkdown from 'react-markdown';

const RCAPanel = ({ narrative, evidence }) => {
  if (!narrative) return null;

  const parsedEvidence = evidence ? JSON.parse(evidence) : null;

  return (
    <div className="p-6 mt-6 bg-white rounded shadow-md">
      <h3 className="mb-4 text-xl font-bold">Root Cause Analysis</h3>
      <div className="p-4 mb-6 text-gray-800 bg-gray-50 rounded">
        <ReactMarkdown>{narrative}</ReactMarkdown>
      </div>
      
      {parsedEvidence && parsedEvidence.ranked_drivers && (
        <table className="w-full text-left border-collapse">
          <thead>
            <tr>
              <th className="p-2 border-b">Feature</th>
              <th className="p-2 border-b">Value</th>
              <th className="p-2 border-b">SHAP Weight</th>
            </tr>
          </thead>
          <tbody>
            {parsedEvidence.ranked_drivers.map((driver, idx) => (
              <tr key={idx}>
                <td className="p-2 border-b font-medium">{driver.feature_name}</td>
                <td className="p-2 border-b">{driver.feature_value}</td>
                <td className={`p-2 border-b ${driver.contribution_weight < 0 ? 'text-red-500' : 'text-green-500'}`}>
                  {driver.contribution_weight}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RCAPanel;