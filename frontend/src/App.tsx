/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React from 'react';

import { RouterProvider, createRouter } from '@tanstack/react-router';

import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles';

import { FONT_FAMILIES } from './constants';
import { AIProvider } from './contexts/AIContext';
import { ActionProvider } from './contexts/ActionContext';
import { AuthProvider } from './contexts/AuthContext';
import { GlobalProvider } from './contexts/GlobalContext';
import { LinkModalProvider } from './contexts/LinkModalContext';
import { MarketplaceProvider } from './contexts/MarketplaceContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { TaskModalProvider } from './contexts/TaskModalContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { TimeFormatProvider } from './contexts/TimeFormatContext';
import { TourProvider } from './contexts/TourContext';
import { UserCacheProvider } from './contexts/UserCacheContext';
import { routeTree } from './routeTree.gen';

const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

const muiTheme = createTheme({
  // Central corner-radius lever: sx `borderRadius: 1` -> 6px, `2` -> 12px,
  // aligning MUI components with the marketplace (7px controls / 12px cards).
  shape: { borderRadius: 6 },
  palette: {
    primary: { main: '#5d68b0' }, // brand indigo — matches var(--accent) in both apps
    error: { main: '#ef4444' },
  },
  typography: {
    fontFamily: FONT_FAMILIES.PRIMARY,
    fontSize: 13, // shared base with marketplace (zoom 1.1 handles overall scale)
  },
  components: {
    MuiTab: {
      styleOverrides: {
        root: { fontFamily: FONT_FAMILIES.PRIMARY },
      },
    },
  },
});

const App: React.FC = () => {
  return (
    <MuiThemeProvider theme={muiTheme}>
      <NotificationProvider>
        <AuthProvider>
          <GlobalProvider>
            <TourProvider>
              <MarketplaceProvider>
                <AIProvider>
                  <ActionProvider>
                    <TaskModalProvider>
                      <LinkModalProvider>
                        <ThemeProvider>
                          <TimeFormatProvider>
                            <UserCacheProvider>
                              <RouterProvider router={router} />
                            </UserCacheProvider>
                          </TimeFormatProvider>
                        </ThemeProvider>
                      </LinkModalProvider>
                    </TaskModalProvider>
                  </ActionProvider>
                </AIProvider>
              </MarketplaceProvider>
            </TourProvider>
          </GlobalProvider>
        </AuthProvider>
      </NotificationProvider>
    </MuiThemeProvider>
  );
};

export default App;
