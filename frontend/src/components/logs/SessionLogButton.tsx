/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import ViewListIcon from '@mui/icons-material/ViewList';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Fab from '@mui/material/Fab';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';

import { getSessionIds, setSessionIdCallback } from '@/services/api';

import LogsExplorer from './LogsExplorer';

/**
 * SessionLogButton Component
 *
 * A floating action button (FAB) positioned in the bottom-right corner that provides
 * access to session logs. The button displays a badge showing the count of available
 * session IDs. Clicking the button opens a dialog listing all available sessions,
 * and selecting a session opens the LogsExplorer to browse logs for that session.
 */
function SessionLogButton() {
  const [sessionIds, setSessionIds] = useState<Set<string>>(new Set());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [initialPath, setInitialPath] = useState<string>('');
  const [explorerOpen, setExplorerOpen] = useState(false);

  useEffect(() => {
    // Initialize with current session IDs
    setSessionIds(getSessionIds());

    // Set up callback to update when new session IDs are added
    setSessionIdCallback((newSessionIds: Set<string>) => {
      setSessionIds(newSessionIds);
    });

    // Cleanup callback on unmount
    return () => {
      setSessionIdCallback(() => {});
    };
  }, []);

  const handleButtonClick = () => {
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const buildHivePathForSession = (sessionId: string): string => {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');

    return `yyyy=${yyyy}/mm=${mm}/dd=${dd}/session_id=${sessionId}/category=API`;
  };

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setInitialPath(buildHivePathForSession(sessionId));
    setDialogOpen(false);
    setExplorerOpen(true);
  };

  const handleCloseExplorer = () => {
    setExplorerOpen(false);
    setSelectedSessionId(null);
    setInitialPath('');
  };

  const sessionIdsArray = Array.from(sessionIds).sort().reverse(); // Most recent first

  return (
    <>
      <Fab
        color="primary"
        aria-label="session logs"
        onClick={handleButtonClick}
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          zIndex: 1300,
        }}
      >
        <Badge badgeContent={sessionIds.size} color="error">
          <ViewListIcon />
        </Badge>
      </Fab>

      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Session Logs</DialogTitle>
        <DialogContent>
          {sessionIdsArray.length === 0 ? (
            <Box p={2}>
              <Typography color="text.secondary">
                No session logs available. Make some API requests to see logs here.
              </Typography>
            </Box>
          ) : (
            <List>
              {sessionIdsArray.map((sessionId) => (
                <ListItem key={sessionId} disablePadding>
                  <ListItemButton onClick={() => handleSessionClick(sessionId)}>
                    <ListItemText
                      primary={`Session: ${sessionId?.substring(0, 8) ?? 'N/A'}...`}
                      secondary={sessionId}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={explorerOpen} onClose={handleCloseExplorer} maxWidth="lg" fullWidth>
        <DialogTitle>
          Session Logs: {selectedSessionId ? `${selectedSessionId?.substring(0, 8)}...` : ''}
        </DialogTitle>
        <DialogContent>
          {initialPath ? (
            <LogsExplorer rootLabel="Session Logs" initialPath={initialPath} />
          ) : (
            <Box p={2}>
              <Typography>No session path available.</Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseExplorer}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default SessionLogButton;
