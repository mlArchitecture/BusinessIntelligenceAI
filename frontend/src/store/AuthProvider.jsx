import React, { useState } from 'react';
import AuthContext from './auth-context';

const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [persona, setPersona] = useState(localStorage.getItem('persona'));

  const loginHandler = (newToken, newPersona) => {
    setToken(newToken);
    setPersona(newPersona);
    localStorage.setItem('token', newToken);
    localStorage.setItem('persona', newPersona);
  };

  const logoutHandler = () => {
    setToken(null);
    setPersona(null);
    localStorage.removeItem('token');
    localStorage.removeItem('persona');
  };

  const contextValue = {
    token,
    persona,
    login: loginHandler,
    logout: logoutHandler,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
