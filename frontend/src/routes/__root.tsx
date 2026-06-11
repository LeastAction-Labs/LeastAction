/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Navigate, Outlet, createRootRoute, useRouterState } from '@tanstack/react-router';

import Backdrop from '@mui/material/Backdrop';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';

import ChatbotWidget from '../components/chatbot/ChatbotWidget';
import NotFound from '../components/errors/NotFound';
import NotFoundGravity from '../components/errors/NotFoundGravity';
import TourPanel from '../components/tour/TourPanel';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useTimeFormat } from '../contexts/TimeFormatContext';

// import SessionLogButton from "../components/SessionLogButton";

function ThemedNotFound() {
  const { theme } = useTheme();
  return theme === 'black' ? <NotFound /> : <NotFoundGravity />;
}

function RootComponent() {
  const { authState, sessionExpired, logout } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { timeZone } = useTimeFormat();

  if (!authState.isAuthenticated && !location.pathname.startsWith('/public')) {
    return <Navigate to="/public/login" search={{ redirect: location.href }} />;
  }

  const goToLogin = () => {
    void logout();
    window.location.href = '/public/login';
  };

  return (
    <>
      <div
        key={timeZone}
        className="min-h-screen relative overflow-hidden"
        style={{
          backgroundColor: 'var(--bg-primary)',
          color: 'var(--text-primary)',
        }}
      >
        <main className="w-full relative z-10">
          <Outlet />
        </main>
        {/* <SessionLogButton /> */}
        {pathname !== '/explore' && <TourPanel />}
        <ChatbotWidget />
      </div>
      {sessionExpired && !pathname.startsWith('/public') && (
        <Backdrop
          open
          onClick={goToLogin}
          sx={{ zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.75)' }}
        >
          <Paper
            onClick={(e) => e.stopPropagation()}
            sx={{
              p: 4,
              textAlign: 'center',
              maxWidth: 360,
              width: '100%',
              borderRadius: 2,
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
            }}
          >
            <Typography variant="h6" gutterBottom sx={{ color: 'var(--text-primary)' }}>
              Session Expired
            </Typography>
            <Typography variant="body2" sx={{ mb: 3, color: 'var(--text-secondary, #666)' }}>
              Your session has expired. Please log in again to continue.
            </Typography>
            <Button variant="contained" onClick={goToLogin} fullWidth>
              Login
            </Button>
          </Paper>
        </Backdrop>
      )}
    </>
  );
}

export const Route = createRootRoute({
  notFoundComponent: ThemedNotFound,
  component: RootComponent,
});
