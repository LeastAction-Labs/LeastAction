/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import {
  CheckCircleOutline as CheckIcon,
  ErrorOutline as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { httpJson } from '@/services/api';

const getThemeStyles = () => ({
  errorLogSection: {
    bgcolor: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 2,
    overflow: 'hidden',
    transition: 'background-color 0.3s ease, border-color 0.3s ease',
  },
  errorLogHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    p: 2,
    borderBottom: '1px solid var(--border)',
    transition: 'border-color 0.3s ease',
    gap: 2,
  },
  datePickerInput: {
    '& .MuiInputBase-root': {
      fontSize: FONT_SIZES.XS,
      height: 32,
      bgcolor: 'var(--bg-tertiary)',
      transition: 'background-color 0.3s ease',
    },
    '& .MuiInputBase-input': {
      py: 0.5,
      px: 1,
      color: 'var(--text-primary)',
      transition: 'color 0.3s ease',
    },
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: 'var(--border)',
    },
  },
  logLevelTabs: {
    minHeight: 36,
    borderBottom: '1px solid var(--border)',
    '& .MuiTabs-indicator': {
      backgroundColor: '#3b82f6',
    },
  },
  logLevelTab: {
    minHeight: 36,
    minWidth: 70,
    px: 2,
    py: 0.5,
    fontSize: FONT_SIZES.XS,
    textTransform: 'none',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    color: 'var(--text-secondary)',
    '&.Mui-selected': {
      color: '#3b82f6',
    },
  },
  errorLogTitle: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
    transition: 'color 0.3s ease',
  },
  refreshButton: {
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease, background-color 0.3s ease',
    '&:hover': {
      color: 'var(--text-primary)',
      bgcolor: 'rgba(128, 128, 128, 0.1)',
    },
  },
  errorLogContent: {
    p: 4,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 200,
  },
  logContainer: {
    maxHeight: 400,
    overflow: 'auto',
    fontFamily: 'monospace',
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-primary)',
    transition: 'color 0.3s ease',
  },
  logTable: {
    width: '100%',
    borderCollapse: 'collapse',
    '& td': {
      py: 0.5,
      px: 1,
      borderBottom: '1px solid var(--border)',
      verticalAlign: 'top',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    '& td:last-child': {
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      width: '100%',
    },
  },
  emptyStateIcon: {
    width: 80,
    height: 80,
    borderRadius: '50%',
    bgcolor: 'var(--bg-tertiary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    mb: 2,
    transition: 'background-color 0.3s ease',
  },
  checkIconLarge: {
    fontSize: 40,
    color: '#16a34a',
  },
  emptyStateTitle: {
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    mb: 1,
    transition: 'color 0.3s ease',
  },
  emptyStateSubtitle: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease',
  },
  errorLogFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    p: 2,
    borderTop: '1px solid var(--border)',
    bgcolor: 'var(--bg-tertiary)',
    transition: 'background-color 0.3s ease, border-color 0.3s ease',
  },
  footerText: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease',
  },
});

interface LogTableViewProps {
  /**
   * Function that returns the log file URL given a date (YYYY-MM-DD)
   */
  buildLogUrl: (date: string) => string;

  /**
   * Title to display in the header
   */
  title?: string;

  /**
   * Whether to enable polling (refetch logs periodically)
   * Only polls when viewing today's date
   */
  enablePolling?: boolean;

  /**
   * Polling interval in milliseconds
   */
  pollingInterval?: number;

  /**
   * Optional callback when refresh button is clicked
   */
  onRefresh?: () => void;

  /**
   * Whether the system is currently running (affects footer text)
   */
  isRunning?: boolean;

  /**
   * Optional loading state from parent
   */
  loading?: boolean;

  /**
   * Whether to show the logger column in the table
   */
  showLoggerColumn?: boolean;
}

type LogLevel = 'ALL' | 'INFO' | 'ERROR' | 'WARNING' | 'DEBUG' | 'CRITICAL';

const LOG_LEVEL_COLORS: Record<string, string> = {
  INFO: '#3b82f6',
  ERROR: '#ef4444',
  WARNING: '#f59e0b',
  DEBUG: '#8b5cf6',
  CRITICAL: '#ef4444',
};

/**
 * Reusable LogTableView Component
 *
 * Displays logs from a file with:
 * - Date picker for selecting which date to view
 * - Log level filtering
 * - Auto-scrolling and "Jump to latest" functionality
 * - Optional polling for real-time updates
 */
export default function LogTableView({
  buildLogUrl,
  title = 'Error Log & Activity',
  enablePolling = false,
  pollingInterval = 8000,
  onRefresh,
  isRunning = false,
  loading = false,
  showLoggerColumn = true,
}: LogTableViewProps) {
  const styles = getThemeStyles();
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const [selectedLogLevel, setSelectedLogLevel] = useState<LogLevel>('ALL');
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const today = new Date();
    return today.toISOString().split('T')[0]; // YYYY-MM-DD format
  });

  // Check if selected date is today
  const isToday = () => {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    return selectedDate === todayStr;
  };

  // Fetch logs
  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setLogsLoading(true);
        const url = buildLogUrl(selectedDate);
        const response = await httpJson<{ content?: string }>(url);

        if (response.content) {
          const lines = response.content.split('\n').filter((l: string) => l.trim() !== '');
          setLogs(lines);
        } else {
          setLogs([]);
        }
      } catch {
        // Silently handle - logs may not exist yet
        setLogs([]);
      } finally {
        setLogsLoading(false);
      }
    };

    // Always fetch once on mount or when dependencies change
    void fetchLogs();

    // Only poll if enabled AND viewing today's date
    if (enablePolling && isToday()) {
      const intervalId = setInterval(() => void fetchLogs(), pollingInterval);
      return () => clearInterval(intervalId);
    }
  }, [buildLogUrl, selectedDate, enablePolling, pollingInterval]);

  // Auto-scroll to bottom only if user hasn't scrolled up
  useEffect(() => {
    if (logContainerRef.current && !isUserScrolledUp) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, isUserScrolledUp, selectedLogLevel]);

  // Detect if user has scrolled up from the bottom
  const handleLogScroll = () => {
    const el = logContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setIsUserScrolledUp(!atBottom);
  };

  const scrollToBottom = () => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
      setIsUserScrolledUp(false);
    }
  };

  // Parse a log line: "2026-02-11 13:16:10 - logger_name - LEVEL - message"
  const parseLogLine = (line: string) => {
    const match = line.match(
      /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+-\s+(.+?)\s+-\s+(INFO|ERROR|WARNING|DEBUG|CRITICAL)\s+-\s+(.*)$/s,
    );
    if (match) {
      return { time: match[2], logger: match[3], level: match[4], message: match[5] };
    }
    return { time: '', logger: '', level: '', message: line };
  };

  // Filter logs based on selected level
  const filteredLogs = logs.filter((line) => {
    if (selectedLogLevel === 'ALL') return true;
    const parsed = parseLogLine(line);
    return parsed.level === selectedLogLevel;
  });

  return (
    <Box sx={styles.errorLogSection}>
      <Box sx={styles.errorLogHeader}>
        <Typography sx={styles.errorLogTitle}>
          <ErrorIcon sx={{ fontSize: 18 }} />
          {title}
        </Typography>
        <Box
          sx={{
            display: 'flex',
            gap: 1,
            alignItems: 'center',
            flex: 1,
            justifyContent: 'flex-end',
          }}
        >
          <TextField
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            sx={styles.datePickerInput}
            size="small"
            InputLabelProps={{ shrink: true }}
          />
          {onRefresh && (
            <IconButton
              sx={styles.refreshButton}
              size="small"
              onClick={onRefresh}
              disabled={loading}
            >
              <RefreshIcon sx={{ fontSize: 18 }} />
            </IconButton>
          )}
        </Box>
      </Box>

      <Tabs
        value={selectedLogLevel}
        onChange={(_, value) => setSelectedLogLevel(value)}
        sx={styles.logLevelTabs}
      >
        <Tab label="All" value="ALL" sx={styles.logLevelTab} />
        <Tab label="Info" value="INFO" sx={styles.logLevelTab} />
        <Tab label="Error" value="ERROR" sx={styles.logLevelTab} />
        <Tab label="Warning" value="WARNING" sx={styles.logLevelTab} />
        <Tab label="Debug" value="DEBUG" sx={styles.logLevelTab} />
        <Tab label="Critical" value="CRITICAL" sx={styles.logLevelTab} />
      </Tabs>

      {logsLoading && logs.length === 0 ? (
        <Box sx={styles.errorLogContent}>
          <CircularProgress size={24} sx={{ color: 'var(--text-secondary)' }} />
        </Box>
      ) : filteredLogs.length > 0 ? (
        <Box sx={{ position: 'relative' }}>
          <Box sx={styles.logContainer} ref={logContainerRef} onScroll={handleLogScroll}>
            <Box component="table" sx={styles.logTable}>
              <tbody>
                {filteredLogs.map((line, idx) => {
                  const parsed = parseLogLine(line);
                  const levelColor = LOG_LEVEL_COLORS[parsed.level] || 'var(--text-secondary)';
                  return (
                    <tr key={idx}>
                      <td
                        style={{
                          color: 'var(--text-secondary)',
                          width: 80,
                          minWidth: 80,
                          maxWidth: 80,
                        }}
                      >
                        {parsed.time}
                      </td>
                      {showLoggerColumn && (
                        <td
                          style={{
                            color: 'var(--text-secondary)',
                            maxWidth: 180,
                            borderLeft: '1px solid var(--border)',
                          }}
                        >
                          {parsed.logger}
                        </td>
                      )}
                      <td
                        style={{
                          color: levelColor,
                          fontWeight: 600,
                          width: 70,
                          minWidth: 70,
                          maxWidth: 70,
                          borderLeft: '1px solid var(--border)',
                        }}
                      >
                        {parsed.level}
                      </td>
                      <td
                        style={{
                          color: 'var(--text-primary)',
                          borderLeft: '1px solid var(--border)',
                        }}
                      >
                        {parsed.message}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </Box>
          </Box>
          {isUserScrolledUp && (
            <Button
              onClick={scrollToBottom}
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 16,
                bgcolor: '#3b82f6',
                color: 'white',
                textTransform: 'none',
                fontSize: FONT_SIZES.XS,
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                minWidth: 'auto',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                '&:hover': { bgcolor: '#2563eb' },
              }}
            >
              Jump to latest
            </Button>
          )}
        </Box>
      ) : (
        <Box sx={styles.errorLogContent}>
          <Box sx={styles.emptyStateIcon}>
            <CheckIcon sx={styles.checkIconLarge} />
          </Box>
          <Typography sx={styles.emptyStateTitle}>
            {selectedLogLevel === 'ALL'
              ? 'No logs found'
              : selectedLogLevel === 'ERROR'
                ? 'No errors detected'
                : selectedLogLevel === 'WARNING'
                  ? 'No warnings detected'
                  : selectedLogLevel === 'CRITICAL'
                    ? 'No critical issues detected'
                    : selectedLogLevel === 'DEBUG'
                      ? 'No debug logs found'
                      : 'No info logs found'}
          </Typography>
          <Typography sx={styles.emptyStateSubtitle}>
            {logs.length > 0
              ? `No ${selectedLogLevel.toLowerCase()} logs in this view.`
              : isToday()
                ? `System is running optimally. Last scan ${Math.floor(pollingInterval / 1000)}s ago.`
                : `No logs available for ${selectedDate}.`}
          </Typography>
        </Box>
      )}

      <Box sx={styles.errorLogFooter}>
        <Typography sx={styles.footerText}>
          {selectedLogLevel === 'ALL'
            ? `Total log lines: ${logs.length.toLocaleString()}`
            : `Showing ${filteredLogs.length.toLocaleString()} of ${logs.length.toLocaleString()} logs`}
        </Typography>
        <Typography sx={styles.footerText}>
          {enablePolling && isToday() && isRunning
            ? `Polling every ${Math.floor(pollingInterval / 1000)}s`
            : 'Not polling'}
        </Typography>
      </Box>
    </Box>
  );
}
