import React, { useState } from 'react';
import api from '../../utils/api';

const Register = () => {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [persona, setPersona] = useState('manager');

  const submitHandler = async (e) => {
    e.preventDefault();
    try {
      await api.post('/signup', { userId, password, persona });
      window.location.href = '/login';
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <form onSubmit={submitHandler} className="p-8 bg-white rounded shadow-md w-96">
        <h2 className="mb-6 text-2xl font-bold">Register</h2>
        <input
          type="text"
          placeholder="User ID"
          className="w-full p-2 mb-4 border rounded"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full p-2 mb-4 border rounded"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <select
          className="w-full p-2 mb-6 border rounded"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
        >
          <option value="manager">Manager</option>
          <option value="analyst">Analyst</option>
        </select>
        <button type="submit" className="w-full p-2 text-white bg-green-600 rounded">
          Create Account
        </button>
      </form>
    </div>
  );
};

export default Register;
