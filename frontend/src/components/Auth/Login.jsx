import React, { useState, useContext } from 'react';
import AuthContext from '../../store/auth-context';
import api from '../../utils/api';

const Login = () => {
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const authCtx = useContext(AuthContext);

  const submitHandler = async (e) => {
    e.preventDefault();
    try {
      const response = await api.post('/login', { userId, password });
      authCtx.login(response.data.access_token, response.data.persona);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <form onSubmit={submitHandler} className="p-8 bg-white rounded shadow-md w-96">
        <h2 className="mb-6 text-2xl font-bold">Login</h2>
        {error && <p className="mb-4 text-red-500">{error}</p>}
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
          className="w-full p-2 mb-6 border rounded"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" className="w-full p-2 text-white bg-blue-600 rounded">
          Authenticate
        </button>
      </form>
    </div>
  );
};

export default Login;
