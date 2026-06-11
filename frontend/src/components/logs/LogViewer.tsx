/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Box, CircularProgress, Typography } from '@mui/material';

import { CORE_BACKEND_URL } from '@/config/urls';
import { httpJson } from '@/services/api';

const DEFAULT_LOGS_STREAM = '/api/v1/logs/stream';

interface TaskSessionLogsResponse {
  task_id: string;
  session_id: string;
  logs: Array<{
    name: string;
    path: string;
    size: number;
    modified: number;
    content: string;
  }>;
  content: string;
  total_count: number;
}

interface LogViewerProps {
  taskId?: string;
  sessionId?: string | null;
}

function resolveLogsStreamUrl(): string {
  const base = CORE_BACKEND_URL;
  if (base) {
    const trimmed = base.endsWith('/') ? base.slice(0, -1) : base;
    return `${trimmed}${DEFAULT_LOGS_STREAM}`;
  }
  return DEFAULT_LOGS_STREAM;
}

function LogViewer({ taskId, sessionId }: LogViewerProps = {}) {
  const [logs, setLogs] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch logs from API if taskId and sessionId are provided
  useEffect(() => {
    if (taskId && sessionId) {
      setLoading(true);
      setError(null);
      setLogs('');

      const fetchLogs = async () => {
        try {
          const apiBaseUrl = CORE_BACKEND_URL || '';
          const base = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
          const url = `${base}/api/v1/logs/task-logs/${taskId}/sessions/${sessionId}`;

          const response = await httpJson<TaskSessionLogsResponse>(url);

          // Use aggregated content which includes all log files with separators
          setLogs(response.content || '');
          setIsConnected(true);
        } catch (err) {
          console.error('Error fetching logs:', err);
          setError(err instanceof Error ? err.message : 'Failed to fetch logs');
          setIsConnected(false);
        } finally {
          setLoading(false);
        }
      };

      void fetchLogs();
      return;
    }

    // Fallback to SSE if no taskId/sessionId provided (backward compatibility)
    const url = resolveLogsStreamUrl();
    const eventSource = new EventSource(url, { withCredentials: true });

    eventSource.onopen = () => {
      setIsConnected(true);
      ////console.log("SSE connection established to", url);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as { content?: string; error?: string };

        if (data.content) {
          setLogs((prevLogs) => prevLogs + data.content);
        }

        if (data.error) {
          setError(data.error);
        }
      } catch (e) {
        console.error('Error parsing SSE log event:', e);
      }
    };

    eventSource.onerror = (evt) => {
      console.error('SSE error:', evt);
      setIsConnected(false);
      setError('Connection error. Reconnecting...');

      setTimeout(() => {
        eventSource.close();
      }, 5000);
    };

    return () => {
      eventSource.close();
    };
  }, [taskId, sessionId]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          p: 3,
        }}
      >
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {!taskId && !sessionId && (
        <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
          {isConnected ? (
            <Typography variant="caption" color="success.main">
              ✅ Connected to log stream
            </Typography>
          ) : (
            <Typography variant="caption" color="error">
              ❌ Disconnected
            </Typography>
          )}
          {error && (
            <Typography variant="caption" color="error" display="block">
              {error}
            </Typography>
          )}
        </Box>
      )}

      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          backgroundColor: '#f5f5f5',
          padding: 2,
          borderRadius: 1,
        }}
      >
        {error ? (
          <Box
            component="div"
            sx={{ color: 'error.main', fontFamily: 'monospace', fontSize: '0.875rem' }}
          >
            Error: {error}
          </Box>
        ) : logs ? (
          <Box
            component="pre"
            sx={{
              margin: 0,
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontSize: '0.875rem',
              lineHeight: 1.6,
              color: 'var(--text-primary)',
            }}
          >
            {logs}
          </Box>
        ) : (
          <Box
            component="div"
            sx={{
              color: 'text.secondary',
              fontStyle: 'italic',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
            }}
          >
            Waiting for logs...
          </Box>
        )}
      </Box>
    </Box>
  );
}

export default LogViewer;
