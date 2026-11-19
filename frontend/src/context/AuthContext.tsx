import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../services/api';

interface AuthContextType {
  isAuthenticated: boolean;
  username: string | null;
  loading: boolean;
  login: (token: string, username: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  username: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const token = localStorage.getItem('zander_auth_token');

    if (token) {
      // Validate token with backend
      api.getProfile()
        .then((profile) => {
          setIsAuthenticated(true);
          setUsername(profile.username);
        })
        .catch(() => {
          localStorage.removeItem('zander_auth_token');
          localStorage.removeItem('zander_user');
          setIsAuthenticated(false);
          setUsername(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setIsAuthenticated(false);
      setUsername(null);
      setLoading(false);
    }
  }, []);

  const login = (token: string, user: string) => {
    localStorage.setItem('zander_auth_token', token);
    localStorage.setItem('zander_user', user);
    setIsAuthenticated(true);
    setUsername(user);
  };

  const logout = () => {
    localStorage.removeItem('zander_auth_token');
    localStorage.removeItem('zander_user');
    setIsAuthenticated(false);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, username, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
