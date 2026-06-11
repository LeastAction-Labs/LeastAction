/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useEffect, useState } from 'react';

import BugReportIcon from '@mui/icons-material/BugReport';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import type { AlertColor } from '@mui/material';
import { Alert, Box, Collapse, IconButton, Snackbar, Tooltip } from '@mui/material';

import type { NotificationPayload } from '@/screens/Browse/handlers/notificationHandlers';

interface Notification {
  id: string;
  message: string;
  severity: AlertColor;
  details?: unknown;
  sessionId?: string;
}

interface NotificationContextType {
  showNotification: (message: string, severity: AlertColor, details?: unknown) => void;
  showSuccess: (message: string) => void;
  showError: (message: string, details?: unknown, sessionId?: string) => void;
  showWarning: (message: string) => void;
  showInfo: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
  defaultAutoHideDuration?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    const handleEvent = (event: Event) => {
      const customEvent = event as CustomEvent<NotificationPayload>;
      const { type, notification } = customEvent.detail;

      if (type === 'success') showSuccess(notification.message);
      if (type === 'error')
        showError(notification.message, notification.detail, notification.sessionId);
    };

    window.addEventListener('SHOW_NOTIFICATION', handleEvent);
    return () => window.removeEventListener('SHOW_NOTIFICATION', handleEvent);
  }, []);

  const showNotification = (
    message: string,
    severity: AlertColor = 'info',
    details?: unknown,
    sessionId?: string,
  ) => {
    const id = crypto.randomUUID();
    setNotifications((prev) => {
      const updated = [...prev, { id, message, severity, details, sessionId }];
      return updated.length > 3 ? updated.slice(updated.length - 3) : updated;
    });
  };

  const showSuccess = (message: string) => showNotification(message, 'success');
  const showError = (message: string, details?: unknown, sessionId?: string) => {
    //console.log('🟣 showError called with:', { message, details });
    showNotification(message, 'error', details, sessionId);
  };
  const showWarning = (message: string) => showNotification(message, 'warning');
  const showInfo = (message: string) => showNotification(message, 'info');

  const handleClose = (id: string) => {
    setNotifications((prev) => prev.filter((notification) => notification.id !== id));
    setExpandedNotifications((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  };

  const handleExited = (id: string) => {
    setNotifications((prev) => prev.filter((notification) => notification.id !== id));
  };

  const [expandedNotifications, setExpandedNotifications] = useState<Set<string>>(new Set());
  const [copiedNotifications, setCopiedNotifications] = useState<Set<string>>(new Set());

  const getFormattedDate = () => {
    const date = new Date();
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const copyToClipboard = (id: string, message: string, details?: unknown) => {
    const text = details ? `${message}\n\n${formatDetails(details)}` : message;
    void navigator.clipboard.writeText(text).then(() => {
      setCopiedNotifications((prev) => new Set(prev).add(id));
      setTimeout(() => {
        setCopiedNotifications((prev) => {
          const next = new Set(prev);
          next.delete(id);
          return next;
        });
      }, 2000);
    });
  };

  const toggleExpanded = (id: string) => {
    setExpandedNotifications((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const formatDetails = (details: unknown): string => {
    if (!details) return '';

    try {
      if (typeof details === 'object' && details !== null) {
        const obj = details as Record<string, unknown>;
        // Format validation results (codeblock errors/warnings)
        if (Array.isArray(obj.errors) || Array.isArray(obj.warnings)) {
          const lines: string[] = [];
          if (Array.isArray(obj.errors)) {
            for (const e of obj.errors) {
              const entry = e as Record<string, unknown>;
              const loc = [entry.file, entry.line].filter(Boolean).join(':');
              lines.push(
                `[${String(entry.code)}] ${String(entry.message)}${loc ? `  ${loc}` : ''}`,
              );
            }
          }
          if (Array.isArray(obj.warnings)) {
            for (const w of obj.warnings) {
              const entry = w as Record<string, unknown>;
              const loc = [entry.file, entry.line].filter(Boolean).join(':');
              lines.push(
                `[${String(entry.code)}] ${String(entry.message)}${loc ? `  ${loc}` : ''}`,
              );
            }
          }
          return lines.join('\n');
        }
        // Pydantic validation errors — format compactly, skip `input` (full request body)
        if (Array.isArray(obj.detail)) {
          return (obj.detail as Record<string, unknown>[])
            .map((e) => {
              const loc = Array.isArray(e.loc) ? e.loc.join(' → ') : '';
              const msg = typeof e.msg === 'string' ? e.msg : JSON.stringify(e.msg);
              const type = typeof e.type === 'string' ? ` [${e.type}]` : '';
              return `${loc ? `${loc}: ` : ''}${msg}${type}`;
            })
            .join('\n');
        }
        return JSON.stringify(details, null, 2);
      }

      return typeof details === 'string' ? details : JSON.stringify(details);
    } catch {
      return 'Unable to display error details';
    }
  };

  return (
    <NotificationContext.Provider
      value={{
        showNotification,
        showSuccess,
        showError,
        showWarning,
        showInfo,
      }}
    >
      {children}

      {/* Render all notifications stacked vertically */}
      {notifications.map((notification, index) => {
        const hasDetails = notification.details !== undefined && notification.details !== null;
        const isExpanded = expandedNotifications.has(notification.id);
        const formattedDetails = hasDetails ? formatDetails(notification.details) : '';
        const isError = notification.severity === 'error';

        return (
          <Snackbar
            key={notification.id}
            open={true}
            autoHideDuration={isError ? null : 5000}
            onClose={(_e, reason) => {
              if (reason !== 'clickaway') handleClose(notification.id);
            }}
            TransitionProps={{ onExited: () => handleExited(notification.id) }}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            sx={{
              bottom: `${16 + index * 80}px !important`,
              maxWidth: 'min(480px, calc(100vw - 32px))',
            }}
          >
            <Alert
              severity={notification.severity}
              variant="filled"
              action={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {/* Debug Button */}
                  {notification.sessionId && (
                    <Tooltip title="Debug">
                      <IconButton
                        size="small"
                        component="a"
                        href={`/debug?session_id=${encodeURIComponent(notification.sessionId)}&session_date=${getFormattedDate()}`}
                        sx={{ color: 'inherit' }}
                      >
                        <BugReportIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}

                  <Tooltip title={copiedNotifications.has(notification.id) ? 'Copied!' : 'Copy'}>
                    <IconButton
                      size="small"
                      onClick={() =>
                        copyToClipboard(notification.id, notification.message, notification.details)
                      }
                      sx={{ color: 'inherit' }}
                    >
                      {copiedNotifications.has(notification.id) ? (
                        <CheckIcon fontSize="small" />
                      ) : (
                        <ContentCopyIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>
                  {hasDetails && (
                    <IconButton
                      size="small"
                      onClick={() => toggleExpanded(notification.id)}
                      sx={{
                        color: 'inherit',
                        transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s',
                      }}
                    >
                      <ExpandMoreIcon />
                    </IconButton>
                  )}
                  <IconButton
                    size="small"
                    onClick={() => handleClose(notification.id)}
                    sx={{ color: 'inherit' }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              }
            >
              <Box>
                {notification.message}
                {hasDetails && (
                  <Collapse in={isExpanded} timeout="auto">
                    <Box
                      sx={{
                        mt: 1,
                        pt: 1,
                        borderTop: '1px solid rgba(255, 255, 255, 0.3)',
                        fontFamily: 'monospace',
                        fontSize: '0.85em',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        maxHeight: '200px',
                        overflow: 'auto',
                      }}
                    >
                      {formattedDetails}
                    </Box>
                  </Collapse>
                )}
              </Box>
            </Alert>
          </Snackbar>
        );
      })}
    </NotificationContext.Provider>
  );
};
