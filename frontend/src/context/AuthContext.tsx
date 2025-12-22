import React, { createContext, useContext, useState, useEffect } from 'react';
import { register, login } from '@/services/auth';
import axios from 'axios';

interface AuthContextType {
  user: { email?: string; username?: string } | null;
  tokens: { accessToken?: string; refreshToken?: string } | null;
  isAuthenticated: boolean;
  registerUser: (email: string, password: string, username: string, fullName: string) => Promise<void>;
  loginUser: (email: string, password: string) => Promise<void>;
  logoutUser: () => void;
  refreshAccessToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<{ email?: string; username?: string } | null>(null);
  const [tokens, setTokens] = useState<{ accessToken?: string; refreshToken?: string } | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Load tokens from localStorage on mount
  useEffect(() => {
    const storedTokens = localStorage.getItem('authTokens');
    const storedUser = localStorage.getItem('authUser');
    if (storedTokens && storedUser) {
      setTokens(JSON.parse(storedTokens));
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);
      // Attach token to axios requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${JSON.parse(storedTokens).accessToken}`;
    }
  }, []);

  const registerUser = async (email: string, password: string, username: string, fullName: string) => {
    try {
      const response = await register(email, password, username, fullName);
      // Save user info (extend with actual user data from backend response)
      setUser({ email, username });
      setIsAuthenticated(true);
      console.log('Registration successful, user created:', response);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const loginUser = async (email: string, password: string) => {
    try {
      const response = await login(email, password);
      // Save tokens and user info from backend response
      const { access_token, refresh_token } = response;
      setTokens({ accessToken: access_token, refreshToken: refresh_token });
      setUser({ email });
      setIsAuthenticated(true);
      // Store in localStorage
      localStorage.setItem('authTokens', JSON.stringify({ accessToken: access_token, refreshToken: refresh_token }));
      localStorage.setItem('authUser', JSON.stringify({ email }));
      // Attach token to axios requests
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      console.log('Login successful, tokens stored:', response);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logoutUser = () => {
    setUser(null);
    setTokens(null);
    setIsAuthenticated(false);
    // Remove from localStorage
    localStorage.removeItem('authTokens');
    localStorage.removeItem('authUser');
    // Remove token from axios headers
    delete axios.defaults.headers.common['Authorization'];
    console.log('User logged out, tokens removed');
  };

  const refreshAccessToken = async () => {
    if (!tokens?.refreshToken) return;
    try {
      const response = await axios.post('http://localhost:8000/api/v1/refresh', {
        refresh_token: tokens.refreshToken
      });
      const newAccessToken = response.data.access_token;
      setTokens(prev => prev ? { ...prev, accessToken: newAccessToken } : null);
      localStorage.setItem('authTokens', JSON.stringify({ ...tokens, accessToken: newAccessToken }));
      axios.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
      console.log('Access token refreshed successfully');
    } catch (error) {
      console.error('Failed to refresh access token:', error);
      logoutUser();
    }
  };

  return (
    <AuthContext.Provider value={{ user, tokens, isAuthenticated, registerUser, loginUser, logoutUser, refreshAccessToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};