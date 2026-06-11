/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import {
  FavoriteBorder as HealthyIcon,
  Pause as PauseIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { Box, Button, CircularProgress, IconButton, Typography } from '@mui/material';

import { useNotification } from '@/contexts/NotificationContext';

import { FONT_SIZES, FONT_WEIGHTS } from '../../constants';
import { useTheme } from '../../contexts/ThemeContext';
import {
  calculateTimeDelta,
  formatTimestamp,
  manageScheduler,
} from '../../services/scheduler.service';
import StreamLogViewer from '../logs/StreamLogViewer';

const SCHEDULER_INTERVAL = 5; // seconds (from system.yml: project_scheduler_interval: 5)

const getThemeStyles = () => ({
  container: {
    flex: 1,
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    overflow: 'auto',
    p: 3,
    height: '100%',
    transition: 'background-color 0.3s ease, color 0.3s ease',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    mb: 3,
  },
  projectInfo: {
    flex: 1,
  },
  projectTitle: {
    fontSize: '20px',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    color: 'var(--text-primary)',
    mb: 0.5,
    transition: 'color 0.3s ease',
  },
  projectDescription: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease',
  },
  headerButtons: {
    display: 'flex',
    gap: 1,
  },
  stopButton: {
    bgcolor: '#dc2626',
    color: 'white',
    textTransform: 'none',
    px: 2.5,
    py: 1,
    borderRadius: 1,
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    border: '1px solid #dc2626',
    '&:hover': {
      bgcolor: '#b91c1c',
      border: '1px solid #b91c1c',
    },
  },
  startButton: {
    bgcolor: '#16a34a',
    color: 'white',
    textTransform: 'none',
    px: 2.5,
    py: 1,
    borderRadius: 1,
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    border: '1px solid #16a34a',
    '&:hover': {
      bgcolor: '#15803d',
      border: '1px solid #15803d',
    },
  },
  refreshButton: {
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease, background-color 0.3s ease',
    '&:hover': {
      color: 'var(--text-primary)',
      bgcolor: 'rgba(128, 128, 128, 0.1)',
    },
  },
  statusGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 2,
    mb: 3,
  },
  statusCard: {
    bgcolor: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    borderRadius: 2,
    p: 3,
    transition: 'background-color 0.3s ease, border-color 0.3s ease',
  },
  cardLabel: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: 1,
    mb: 2,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    transition: 'color 0.3s ease',
  },
  statusHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
    mb: 3,
  },
  statusBadge: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 48,
    height: 48,
    borderRadius: '50%',
    bgcolor: 'var(--bg-tertiary)',
    transition: 'background-color 0.3s ease',
  },
  playIcon: {
    fontSize: 24,
    color: '#16a34a',
  },
  pauseIcon: {
    fontSize: 24,
    color: '#f97316',
  },
  statusText: {
    fontSize: '28px',
    fontWeight: FONT_WEIGHTS.BOLD,
    color: 'var(--text-primary)',
    letterSpacing: 1,
    transition: 'color 0.3s ease',
  },
  infoRow: {
    mb: 1.5,
  },
  infoRowGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 2,
    mb: 1.5,
  },
  infoColumn: {
    display: 'flex',
    flexDirection: 'column',
  },
  infoLabel: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
    mb: 0.25,
    transition: 'color 0.3s ease',
  },
  infoValue: {
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
    fontFamily: 'monospace',
    transition: 'color 0.3s ease',
  },
  heartbeatDate: {
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
    mb: 0.5,
    transition: 'color 0.3s ease',
  },
  heartbeatTime: {
    fontSize: '32px',
    fontWeight: FONT_WEIGHTS.BOLD,
    color: '#3b82f6',
    fontFamily: 'monospace',
    mb: 2,
    letterSpacing: 2,
  },
  healthyBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    bgcolor: 'transparent',
    color: '#16a34a',
    border: '1px solid #16a34a',
    px: 1.5,
    py: 0.5,
    borderRadius: 1,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    textTransform: 'uppercase',
    mb: 2,
  },
  inactiveBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    bgcolor: 'transparent',
    color: '#f97316',
    border: '1px solid #f97316',
    px: 1.5,
    py: 0.5,
    borderRadius: 1,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    textTransform: 'uppercase',
    mb: 2,
  },
  errorBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    bgcolor: 'transparent',
    color: '#dc2626',
    border: '1px solid #dc2626',
    px: 1.5,
    py: 0.5,
    borderRadius: 1,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    textTransform: 'uppercase',
    mb: 2,
  },
  unhealthyBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    bgcolor: 'transparent',
    color: '#f59e0b',
    border: '1px solid #f59e0b',
    px: 1.5,
    py: 0.5,
    borderRadius: 1,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    textTransform: 'uppercase',
    mb: 2,
  },
  nextHeartbeat: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
    transition: 'color 0.3s ease',
  },
});

type CronStatusType = 'RUNNING' | 'STOPPED' | 'ERROR' | 'STARTED' | 'STOP';

interface SchedulerData {
  cron_status?: CronStatusType;
  latest_heartbeat?: string;
  start_date?: string;
  stop_date?: string;
  updated_at?: string;
  project_laui?: string;
  error?: string | null;
  message?: string;
}

interface SchedulerTabProps {
  projectLaui: string;
  projectName?: string;
  schedulerData?: SchedulerData | null;
  onRefresh?: () => void;
}

/**
 * SchedulerTab Component
 * Displays the scheduler state for a project and allows starting/stopping it.
 * Status is driven by cron_status from the backend (RUNNING, STOPPED, ERROR).
 */
export default function SchedulerTab({
  projectLaui,
  projectName,
  schedulerData,
  onRefresh,
}: SchedulerTabProps) {
  const { showSuccess } = useNotification();
  useTheme();
  const styles = getThemeStyles();
  const [loading, setLoading] = useState(false);
  const [currentState, setCurrentState] = useState<CronStatusType>(
    schedulerData?.cron_status || 'STOPPED',
  );
  const [selectedLogDate, setSelectedLogDate] = useState<string>(
    new Date().toISOString().split('T')[0],
  );
  const [lastHeartbeat, setLastHeartbeat] = useState<string | undefined>(
    schedulerData?.latest_heartbeat,
  );
  const [confirmAction, setConfirmAction] = useState<'FORCE_START' | 'FORCE_STOP' | null>(null);
  const isUpdatingRef = useRef(false);

  useEffect(() => {
    // Only update state from props if we're not in the middle of an action
    if (schedulerData && !isUpdatingRef.current) {
      setCurrentState(schedulerData.cron_status || 'STOPPED');
      setLastHeartbeat(schedulerData.latest_heartbeat);
    }
  }, [schedulerData]);

  // Poll for scheduler status every 5 seconds, but only while RUNNING
  useEffect(() => {
    if (!onRefresh || currentState !== 'RUNNING') return;
    const intervalId = setInterval(onRefresh, SCHEDULER_INTERVAL * 1000);
    return () => clearInterval(intervalId);
  }, [onRefresh, currentState]);

  const effectiveState = currentState;
  const isRunning = effectiveState === 'RUNNING' || effectiveState === 'STARTED';
  const isUnhealthy =
    isRunning && !!lastHeartbeat && calculateTimeDelta(lastHeartbeat) > 3 * SCHEDULER_INTERVAL;

  // Format heartbeat timestamp
  const formattedHeartbeat = lastHeartbeat ? formatTimestamp(lastHeartbeat) : null;

  // Calculate time until next expected heartbeat (based on scheduler interval, not max delta)
  const getNextHeartbeatInfo = (): string | null => {
    if (!lastHeartbeat) return null;

    const delta = calculateTimeDelta(lastHeartbeat);
    const remaining = SCHEDULER_INTERVAL - (delta % SCHEDULER_INTERVAL);

    if (remaining > 0 && remaining <= SCHEDULER_INTERVAL) {
      return `Next expected heartbeat in ~${remaining}s`;
    }
    return null;
  };

  const handleStartClick = () => {
    if (isRunning) {
      setConfirmAction('FORCE_START');
    } else {
      void handleSchedulerAction('START');
    }
  };

  const handleStopClick = () => {
    const isStopped =
      effectiveState === 'STOPPED' || effectiveState === 'STOP' || effectiveState === 'ERROR';
    if (isStopped) {
      setConfirmAction('FORCE_STOP');
    } else {
      void handleSchedulerAction('STOP');
    }
  };

  const handleConfirm = () => {
    if (confirmAction === 'FORCE_START') {
      void handleSchedulerAction('START');
    } else if (confirmAction === 'FORCE_STOP') {
      void handleSchedulerAction('STOP');
    }
    setConfirmAction(null);
  };

  const handleSchedulerAction = async (action: 'START' | 'STOP') => {
    setLoading(true);
    isUpdatingRef.current = true;
    try {
      const response = await manageScheduler(projectLaui, action);

      // Update local state with response
      setCurrentState((response.cron_status as CronStatusType) || 'STOPPED');
      if (response.latest_heartbeat) {
        setLastHeartbeat(response.latest_heartbeat);
      }

      // Show success notification
      const message =
        action === 'START'
          ? `✓ Scheduler started successfully`
          : `✓ Scheduler stopped successfully`;
      showSuccess(message);

      // Trigger background refresh but don't let it override our state immediately
      if (onRefresh) {
        // Delay the refresh to allow backend to fully update
        setTimeout(() => {
          onRefresh();
          isUpdatingRef.current = false;
        }, 2000);
      } else {
        setTimeout(() => {
          isUpdatingRef.current = false;
        }, 5000);
      }
    } catch (error) {
      console.error(`Error ${action.toLowerCase()}ing scheduler:`, error);
      isUpdatingRef.current = false;
    } finally {
      setLoading(false);
    }
  };

  // Calculate uptime/stopped time
  const getUptime = (): string => {
    if (isRunning) {
      // For running state: calculate uptime using start_date and last_heartbeat
      if (!schedulerData?.start_date || !lastHeartbeat) {
        return '0d 0h 0m';
      }

      const startTime = new Date(schedulerData.start_date).getTime();
      const heartbeatTime = new Date(lastHeartbeat).getTime();
      const delta = Math.floor((heartbeatTime - startTime) / 1000); // in seconds

      if (delta < 0) return '0d 0h 0m';

      const days = Math.floor(delta / 86400);
      const hours = Math.floor((delta % 86400) / 3600);
      const minutes = Math.floor((delta % 3600) / 60);

      return `${days}d ${hours}h ${minutes}m`;
    } else {
      // For stopped state: show stopped time
      if (!schedulerData?.stop_date) {
        return 'Stopped';
      }

      const stopTime = new Date(schedulerData.stop_date).getTime();
      const currentTime = Date.now();
      const delta = Math.floor((currentTime - stopTime) / 1000); // in seconds

      if (delta < 0) return 'Stopped';

      const days = Math.floor(delta / 86400);
      const hours = Math.floor((delta % 86400) / 3600);
      const minutes = Math.floor((delta % 3600) / 60);

      return `Stopped ${days}d ${hours}h ${minutes}m ago`;
    }
  };

  // Get process ID (placeholder)
  const getProcessId = (): string => {
    return 'None';
  };

  // Format start time
  const getStartTime = (): string => {
    if (!schedulerData?.start_date) {
      return 'N/A';
    }
    const formatted = formatTimestamp(schedulerData.start_date);
    return formatted ? `${formatted.date} ${formatted.time}` : 'N/A';
  };

  // Format stop time
  const getStopTime = (): string => {
    if (!schedulerData?.stop_date) {
      return 'N/A';
    }
    const formatted = formatTimestamp(schedulerData.stop_date);
    return formatted ? `${formatted.date} ${formatted.time}` : 'N/A';
  };

  // Get project interval
  const getProjectInterval = (): string => {
    return `${SCHEDULER_INTERVAL}s`;
  };

  // Format project name - use projectName if available, otherwise fall back to projectLaui
  const getProjectName = (): string => {
    return projectName || projectLaui;
  };

  return (
    <Box sx={styles.container}>
      {/* Header */}
      <Box sx={styles.header}>
        <Box sx={styles.projectInfo}>
          <Typography sx={styles.projectTitle}>{getProjectName()}</Typography>
          <Typography sx={styles.projectDescription}>
            Automated workflow for daily data synchronization.
          </Typography>
        </Box>
        <Box sx={styles.headerButtons}>
          {loading ? (
            <CircularProgress
              size={24}
              sx={{ color: 'var(--text-secondary)', transition: 'color 0.3s ease' }}
            />
          ) : (
            <>
              <Button
                variant="contained"
                onClick={handleStartClick}
                sx={styles.startButton}
                disabled={loading}
              >
                Start Scheduler
              </Button>
              <Button
                variant="contained"
                onClick={handleStopClick}
                sx={styles.stopButton}
                disabled={loading}
              >
                Stop Scheduler
              </Button>
            </>
          )}
          <IconButton sx={styles.refreshButton} onClick={onRefresh} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Confirmation Card */}
      {confirmAction && (
        <Box
          sx={{
            bgcolor: 'var(--bg-secondary)',
            border: `1px solid ${confirmAction === 'FORCE_START' ? '#16a34a' : '#dc2626'}`,
            borderRadius: 2,
            p: 2.5,
            mb: 3,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
          }}
        >
          <Box>
            <Typography
              sx={{
                fontSize: FONT_SIZES.SM,
                fontWeight: FONT_WEIGHTS.WEIGHT_600,
                color: confirmAction === 'FORCE_START' ? '#16a34a' : '#dc2626',
                mb: 0.5,
              }}
            >
              {confirmAction === 'FORCE_START' ? 'Force Start Scheduler?' : 'Force Stop Scheduler?'}
            </Typography>
            <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
              {confirmAction === 'FORCE_START'
                ? 'The scheduler is currently running. Are you sure you want to force start it again?'
                : 'The scheduler is already stopped or unhealthy. Are you sure you want to force stop it?'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            <Button
              variant="contained"
              onClick={handleConfirm}
              sx={{
                bgcolor: confirmAction === 'FORCE_START' ? '#16a34a' : '#dc2626',
                color: 'white',
                textTransform: 'none',
                px: 2.5,
                py: 0.75,
                borderRadius: 1,
                fontSize: FONT_SIZES.SM,
                fontWeight: FONT_WEIGHTS.WEIGHT_600,
                '&:hover': {
                  bgcolor: confirmAction === 'FORCE_START' ? '#15803d' : '#b91c1c',
                },
              }}
            >
              Yes
            </Button>
            <Button
              variant="outlined"
              onClick={() => setConfirmAction(null)}
              sx={{
                color: 'var(--text-secondary)',
                borderColor: 'var(--border)',
                textTransform: 'none',
                px: 2.5,
                py: 0.75,
                borderRadius: 1,
                fontSize: FONT_SIZES.SM,
                fontWeight: FONT_WEIGHTS.WEIGHT_600,
                '&:hover': {
                  bgcolor: 'rgba(128,128,128,0.1)',
                  borderColor: 'var(--text-secondary)',
                },
              }}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      )}

      {/* Status Grid */}
      <Box sx={styles.statusGrid}>
        {/* Current Status Card */}
        <Box sx={styles.statusCard}>
          <Typography sx={styles.cardLabel}>CURRENT STATUS</Typography>
          <Box sx={styles.statusHeader}>
            <Box sx={styles.statusBadge}>
              {isRunning ? (
                <PlayArrowIcon sx={styles.playIcon} />
              ) : (
                <PauseIcon sx={styles.pauseIcon} />
              )}
            </Box>
            <Typography sx={styles.statusText}>{effectiveState}</Typography>
          </Box>
          <Box sx={styles.infoRowGrid}>
            <Box sx={styles.infoColumn}>
              <Typography sx={styles.infoLabel}>Uptime</Typography>
              <Typography sx={styles.infoValue}>{getUptime()}</Typography>
            </Box>
            <Box sx={styles.infoColumn}>
              <Typography sx={styles.infoLabel}>Start Time</Typography>
              <Typography sx={styles.infoValue}>{getStartTime()}</Typography>
            </Box>
            <Box sx={styles.infoColumn}>
              <Typography sx={styles.infoLabel}>Stop Time</Typography>
              <Typography sx={styles.infoValue}>{getStopTime()}</Typography>
            </Box>
          </Box>
          <Box sx={styles.infoRow}>
            <Typography sx={styles.infoLabel}>Project Interval</Typography>
            <Typography sx={styles.infoValue}>{getProjectInterval()}</Typography>
          </Box>
          <Box sx={styles.infoRow}>
            <Typography sx={styles.infoLabel}>Process ID</Typography>
            <Typography sx={styles.infoValue}>{getProcessId()}</Typography>
          </Box>
          {effectiveState === 'ERROR' && schedulerData?.error && (
            <Box sx={{ ...styles.infoRow, mt: 1 }}>
              <Typography sx={styles.infoLabel}>Error</Typography>
              <Typography sx={{ ...styles.infoValue, color: '#dc2626' }}>
                {schedulerData.error}
              </Typography>
            </Box>
          )}
        </Box>

        {/* Latest Heartbeat Card */}
        <Box sx={styles.statusCard}>
          <Typography sx={styles.cardLabel}>LATEST HEARTBEAT</Typography>
          {formattedHeartbeat ? (
            <>
              <Typography sx={styles.heartbeatDate}>{formattedHeartbeat.date}</Typography>
              <Typography sx={styles.heartbeatTime}>{formattedHeartbeat.time}</Typography>
              <Box
                sx={
                  isUnhealthy
                    ? styles.unhealthyBadge
                    : isRunning
                      ? styles.healthyBadge
                      : effectiveState === 'ERROR'
                        ? styles.errorBadge
                        : styles.inactiveBadge
                }
              >
                <HealthyIcon sx={{ fontSize: 14, mr: 0.5 }} />
                {isUnhealthy
                  ? 'Unhealthy'
                  : isRunning
                    ? 'Healthy'
                    : effectiveState === 'ERROR'
                      ? 'Error'
                      : 'Inactive'}
              </Box>
              {getNextHeartbeatInfo() && isRunning && (
                <Typography sx={styles.nextHeartbeat}>{getNextHeartbeatInfo()}</Typography>
              )}
            </>
          ) : (
            <Typography
              sx={{
                color: 'var(--text-secondary)',
                mt: 2,
                transition: 'color 0.3s ease',
              }}
            >
              No heartbeat data available
            </Typography>
          )}
        </Box>
      </Box>

      {/* Error Log & Activity Section */}
      <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Typography
          sx={{
            fontSize: FONT_SIZES.SM,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Error Log & Activity
        </Typography>
        <input
          type="date"
          value={selectedLogDate}
          max={new Date().toISOString().split('T')[0]}
          onChange={(e) => setSelectedLogDate(e.target.value)}
          style={{
            padding: '3px 8px',
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            fontSize: 12,
            outline: 'none',
          }}
        />
      </Box>
      <StreamLogViewer
        logFileUrl={(() => {
          const [yyyy, mm, dd] = selectedLogDate.split('-');
          return `file/category=CRON/project=${projectLaui}/yyyy=${yyyy}/mm=${mm}/dd=${dd}/cron.log`;
        })()}
        title=""
        enablePolling={isRunning && selectedLogDate === new Date().toISOString().split('T')[0]}
        pollingInterval={5000}
        onRefresh={onRefresh}
        maxHeight={400}
        paginated={true}
        pageSize={400}
      />
    </Box>
  );
}
