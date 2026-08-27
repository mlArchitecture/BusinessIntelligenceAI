import { createContext } from 'react';

const AuthContext = createContext({
  token: null,
  persona: null,
  login: (token, persona) => {},
  logout: () => {},
});

export default AuthContext;
