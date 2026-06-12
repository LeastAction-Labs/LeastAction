/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';

import axios from 'axios';

import { CORE_BACKEND_URL, CORE_FRONTEND_URL } from '@/config/urls';
import { adminCheck } from '@/services/admin.service';
import { setUnauthorizedCallback } from '@/services/api';

interface User {
  id: string;
  username: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isAdmin: boolean;
  systemUserLaui: string | null;
}

export interface AuthContextType {
  authState: AuthState;
  changeAuthState: (authState: AuthState) => void;
  logout: () => Promise<void>;
  sessionExpired: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isAdmin: false,
    systemUserLaui: null,
  });

  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const changeAuthState = (newAuthState: AuthState) => setAuthState(newAuthState);

  useEffect(() => {
    setUnauthorizedCallback(() => {
      if (authState.isAuthenticated) setSessionExpired(true);
    });
  }, [authState.isAuthenticated]);

  const logout = async () => {
    await axios.post(`${CORE_BACKEND_URL}/api/v1/logout`, {}, { withCredentials: true });
    localStorage.removeItem('la_state');
    localStorage.removeItem('auth_request_started');
    setAuthState({ isAuthenticated: false, user: null, isAdmin: false, systemUserLaui: null });
  };

  useEffect(() => {
    const authRequest = async () => {
      try {
        await axios.get(`${CORE_BACKEND_URL}/api/v1/check_frontend_token_present`, {
          withCredentials: true,
        });
        // I am unable to read httpOnly = True Cookies  , so I went with this approach
        // we can read the cookies from fronted if we set httpOnly = False but that will lead to XSS attacks
        setSessionExpired(false);
        try {
          const systemUserLaui = await adminCheck();
          setAuthState({
            isAuthenticated: true,
            user: null,
            isAdmin: true,
            systemUserLaui,
          });
        } catch {
          setAuthState({
            isAuthenticated: true,
            user: null,
            isAdmin: false,
            systemUserLaui: null,
          });
        }
        return;
      } catch {
        if (!localStorage.getItem('auth_request_started')) {
          // to prevent looping ,  once we come to frontend/callback during the whole auth flow
          // at the end of the flow i am removing this key from localstorage
          const redirect_uri = `${CORE_FRONTEND_URL}/public/callback`;
          const state = crypto.randomUUID();
          localStorage.setItem('la_state', state);
          localStorage.setItem('auth_request_started', 'true');
          window.location.replace(
            `${CORE_BACKEND_URL}/api/v1/auth?client_id=frontend&redirect_uri=${redirect_uri}&state=${state}`,
          );
        }
      } finally {
        setLoading(false);
      }
    };
    void authRequest();
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: 'var(--bg-primary, #fff)',
          color: 'var(--text-primary, #333)',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        <div
          style={{
            width: '36px',
            height: '36px',
            border: '3px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ authState, changeAuthState, logout, sessionExpired }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
