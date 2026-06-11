/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import { Box, Button, CircularProgress, Typography } from '@mui/material';

import { COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { STATUS_COLORS } from '@/constants/logConstants';
import { useTheme } from '@/contexts/ThemeContext';
import { parseDate, today, useTaskHistory } from '@/hooks/useTaskHistory';
import type { LatestFile, TaskHistoryEntry } from '@/hooks/useTaskHistory';
import { formatDateOnly } from '@/utils/timeFormat';

import SessionDetailView from './SessionDetailView';
import TaskHistoryView from './TaskHistoryView';

// Re-export types so existing imports from this file still work
export type { TaskHistoryEntry, LatestFile };

interface DateCard {
  date: string;
  displayDate: string;
  sessions: { sessionId: string; status: string }[];
}

export interface TaskLogsTabProps {
  taskLaui: string;
  logicalDate?: string;
  initialSessionId?: string;
  onSessionChange?: (sessionId: string | null) => void;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDisplayDate(dateStr: string) {
  return formatDateOnly(dateStr);
}

// ── Component ────────────────────────────────────────────────────────────────

export default function TaskLogsTab({
  taskLaui,
  logicalDate,
  initialSessionId,
  onSessionChange,
}: TaskLogsTabProps) {
  const { theme } = useTheme();
  const defaultDateTo = logicalDate ? parseDate(logicalDate) : today();
  const defaultDateFrom = (() => {
    const d = new Date(defaultDateTo);
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  })();
  const [dateFrom, setDateFrom] = useState(defaultDateFrom);
  const [dateTo, setDateTo] = useState(defaultDateTo);
  const [selectedEntry, setSelectedEntry] = useState<TaskHistoryEntry | null>(null);

  const {
    entries: allEntries,
    latestFiles,
    loading,
    refetch: fetchData,
  } = useTaskHistory(taskLaui, dateFrom, dateTo);

  const dateCards = useMemo<DateCard[]>(() => {
    const byDate = new Map<string, TaskHistoryEntry[]>();
    for (const entry of allEntries) {
      const d = entry._date;
      if (!byDate.has(d)) byDate.set(d, []);
      byDate.get(d)!.push(entry);
    }
    return [...byDate.entries()]
      .sort(([a], [b]) => b.localeCompare(a))
      .map(([date, entries]) => ({
        date,
        displayDate: formatDisplayDate(date),
        sessions: [...entries]
          .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
          .map((e) => ({ sessionId: e.session_id, status: e.status })),
      }));
  }, [allEntries]);

  useEffect(() => {
    if (initialSessionId && allEntries.length > 0 && !selectedEntry) {
      const match = allEntries.find((e) => e.session_id === initialSessionId);
      if (match) setSelectedEntry(match);
    }
  }, [allEntries, initialSessionId]);

  const handleBlockClick = (sessionId: string, date: string) => {
    const entry =
      allEntries.find((e) => e.session_id === sessionId) ??
      ({ session_id: sessionId, _date: date } as TaskHistoryEntry);
    setSelectedEntry(entry);
    onSessionChange?.(sessionId);
  };

  const handleSessionClick = (sessionId: string, date: string) => {
    const entry =
      allEntries.find((e) => e.session_id === sessionId) ??
      ({ session_id: sessionId, _date: date } as TaskHistoryEntry);
    setSelectedEntry(entry);
    onSessionChange?.(sessionId);
  };

  const handleBackToHistory = () => {
    setSelectedEntry(null);
    onSessionChange?.(null);
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <Box sx={{ display: 'flex', height: 'calc(100vh - 250px)', overflow: 'hidden' }}>
      {/* ── Left Sidebar ──────────────────────────────────────────────────── */}
      <Box
        sx={{
          width: 220,
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'var(--bg-secondary)',
          overflow: 'hidden',
        }}
      >
        {/* Date range picker */}
        <Box
          sx={{
            px: 1.5,
            pt: 1.5,
            pb: 1,
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}
        >
          <Typography
            sx={{
              fontSize: FONT_SIZES.XS,
              color: 'var(--text-secondary)',
              mb: 0.5,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
            }}
          >
            Date Range
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <input
              type="date"
              value={dateFrom}
              max={dateTo}
              onChange={(e) => setDateFrom(e.target.value)}
              style={{
                width: '100%',
                padding: '4px 8px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                fontSize: FONT_SIZES.XXS,
                outline: 'none',
                boxSizing: 'border-box',
                colorScheme: theme === 'white' ? 'light' : 'dark',
              }}
            />
            <input
              type="date"
              value={dateTo}
              min={dateFrom}
              onChange={(e) => setDateTo(e.target.value)}
              style={{
                width: '100%',
                padding: '4px 8px',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                fontSize: FONT_SIZES.XXS,
                outline: 'none',
                boxSizing: 'border-box',
                colorScheme: theme === 'white' ? 'light' : 'dark',
              }}
            />
          </Box>
        </Box>

        {/* VIEW TASK HISTORY button */}
        <Box sx={{ px: 1, py: 0.75, borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <Button
            fullWidth
            onClick={handleBackToHistory}
            sx={{
              textTransform: 'none',
              color: selectedEntry ? 'var(--text-primary)' : COLORS.BLUE,
              fontSize: FONT_SIZES.XS,
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
              justifyContent: 'center',
              bgcolor: selectedEntry ? 'var(--bg-tertiary)' : COLORS.BLUE_SUBTLE,
              border: '1px solid',
              borderColor: selectedEntry ? 'var(--border)' : COLORS.BLUE,
              borderRadius: 1.5,
              py: 0.5,
              '&:hover': {
                bgcolor: COLORS.BLUE_BG,
                borderColor: COLORS.BLUE,
                color: COLORS.BLUE,
              },
            }}
          >
            VIEW TASK HISTORY
          </Button>
        </Box>

        <Typography
          sx={{
            fontSize: FONT_SIZES.XS,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-secondary)',
            px: 1.5,
            py: 0.75,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            flexShrink: 0,
          }}
        >
          RECENT SESSIONS
        </Typography>

        {/* Date cards with session blocks */}
        <Box sx={{ flex: 1, overflow: 'auto', px: 1, pb: 1 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
              <CircularProgress size={18} sx={{ color: 'var(--text-secondary)' }} />
            </Box>
          ) : dateCards.length === 0 ? (
            <Box sx={{ py: 3, textAlign: 'center' }}>
              <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
                No sessions found
              </Typography>
            </Box>
          ) : (
            dateCards.map((card) => {
              const successCount = card.sessions.filter((s) => s.status === 'success').length;
              const failedCount = card.sessions.filter(
                (s) => s.status === 'failed' || s.status === 'error',
              ).length;

              return (
                <Box key={card.date} sx={{ mb: 1.5 }}>
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      fontWeight: FONT_WEIGHTS.WEIGHT_600,
                      color: 'var(--text-secondary)',
                      mb: 0.5,
                    }}
                  >
                    {card.displayDate}
                  </Typography>

                  <Box
                    sx={{
                      p: 1,
                      borderRadius: 1.5,
                      border: '1px solid var(--border)',
                      bgcolor: 'var(--bg-primary)',
                    }}
                  >
                    {/* Clickable session blocks */}
                    <Box
                      sx={{
                        display: 'flex',
                        gap: 0.5,
                        flexWrap: 'wrap',
                        mb: 0.75,
                      }}
                    >
                      {card.sessions.map((sess) => {
                        const isSelected = selectedEntry?.session_id === sess.sessionId;
                        const color = (STATUS_COLORS[sess.status] ?? STATUS_COLORS.pending).dot;
                        return (
                          <Box
                            key={sess.sessionId}
                            onClick={() => handleBlockClick(sess.sessionId, card.date)}
                            title={sess.sessionId?.substring(0, 8) ?? ''}
                            sx={{
                              width: 20,
                              height: 10,
                              borderRadius: 0.5,
                              bgcolor: color,
                              cursor: 'pointer',
                              outline: isSelected ? `2px solid ${color}` : 'none',
                              outlineOffset: 1,
                              opacity: isSelected ? 1 : 0.6,
                              transition: 'all 0.15s ease',
                              '&:hover': {
                                opacity: 1,
                                transform: 'scaleY(1.25)',
                              },
                            }}
                          />
                        );
                      })}
                    </Box>

                    {/* Success / Failed summary */}
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {successCount > 0 && (
                        <Typography
                          sx={{
                            fontSize: '0.6rem',
                            color: STATUS_COLORS.success.text,
                            fontWeight: FONT_WEIGHTS.WEIGHT_600,
                          }}
                        >
                          {successCount} Success
                        </Typography>
                      )}
                      {failedCount > 0 && (
                        <Typography
                          sx={{
                            fontSize: '0.6rem',
                            color: STATUS_COLORS.failed.text,
                            fontWeight: FONT_WEIGHTS.WEIGHT_600,
                          }}
                        >
                          {failedCount} Failed
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Box>
              );
            })
          )}
        </Box>
      </Box>

      {/* ── Right Panel ───────────────────────────────────────────────────── */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selectedEntry ? (
          <SessionDetailView
            key={`${selectedEntry.session_id}-${selectedEntry._date}`}
            taskLaui={taskLaui}
            sessionId={selectedEntry.session_id}
            sessionDate={selectedEntry._date}
            logicalDate={selectedEntry.logical_date}
            startTime={selectedEntry.start_time}
          />
        ) : (
          <TaskHistoryView
            entries={allEntries}
            loading={loading}
            latestFiles={latestFiles}
            onSessionClick={handleSessionClick}
            onRefresh={fetchData}
          />
        )}
      </Box>
    </Box>
  );
}
