/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import {
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { Box, CircularProgress, Collapse, Typography } from '@mui/material';
import { IconButton } from '@mui/material';

import { COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { STATUS_COLORS } from '@/constants/logConstants';
import { formatDateOnly, formatDateTimeFull } from '@/utils/timeFormat';

import StreamLogViewer from './StreamLogViewer';
import type { LatestFile, TaskHistoryEntry } from './TaskLogsTab';

// ── Props ────────────────────────────────────────────────────────────────────

export interface TaskHistoryViewProps {
  entries: TaskHistoryEntry[];
  loading: boolean;
  latestFiles?: LatestFile[];
  onSessionClick: (sessionId: string, date: string) => void;
  onRefresh?: () => void;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (seconds == null || isNaN(seconds)) return 'N/A';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function formatTime(isoStr: string): string {
  return formatDateTimeFull(isoStr);
}

function formatLogicalTime(logicalDate: string): string {
  if (!logicalDate) return '';
  return logicalDate;
}

function formatLogicalDate(dateStr: string): string {
  return formatDateOnly(dateStr);
}

function getErrorMessage(entry: TaskHistoryEntry): string | null {
  if (entry.status !== 'failed' && entry.status !== 'error') return null;
  try {
    const msg = entry.output?.run_output?.result?.message;
    if (typeof msg === 'string') return msg;
    if (entry.output) return JSON.stringify(entry.output, null, 2);
  } catch {
    /* ignore */
  }
  return null;
}

// ── Component ────────────────────────────────────────────────────────────────

type StatusFilter = 'all' | 'success' | 'error' | 'running' | 'cancelled';

const STATUS_FILTER_OPTIONS: {
  label: string;
  value: StatusFilter;
  color: string;
  matches: string[];
}[] = [
  { label: 'All', value: 'all', color: 'var(--text-secondary)', matches: [] },
  { label: 'Success', value: 'success', color: COLORS.GREEN, matches: ['success'] },
  { label: 'Error', value: 'error', color: COLORS.RED, matches: ['error', 'failed'] },
  { label: 'Cancelled', value: 'cancelled', color: COLORS.PURPLE, matches: ['cancelled'] },
];

export default function TaskHistoryView({
  entries,
  loading,
  latestFiles = [],
  onSessionClick,
  onRefresh,
}: TaskHistoryViewProps) {
  const [latestOpen, setLatestOpen] = useState(false);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const activeFilterOpt = STATUS_FILTER_OPTIONS.find((o) => o.value === statusFilter)!;
  const filteredEntries =
    statusFilter === 'all'
      ? entries
      : entries.filter((e) => activeFilterOpt.matches.includes(e.status));

  // Group entries that share the same logical_date (same scheduled run slot, e.g. retries)
  const groupedEntries = filteredEntries.reduce<
    { logical_date: string; entries: TaskHistoryEntry[] }[]
  >((groups, entry) => {
    const existing = groups.find((g) => g.logical_date === entry.logical_date);
    if (existing) existing.entries.push(entry);
    else groups.push({ logical_date: entry.logical_date, entries: [entry] });
    return groups;
  }, []);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 1,
          }}
        >
          <Typography
            sx={{
              fontSize: FONT_SIZES.LG,
              fontWeight: FONT_WEIGHTS.BOLD,
              color: 'var(--text-primary)',
              letterSpacing: '0.05em',
            }}
          >
            EXECUTION LOG
          </Typography>
          {onRefresh && (
            <IconButton
              onClick={onRefresh}
              disabled={loading}
              size="small"
              sx={{
                color: 'var(--text-secondary)',
                '&:hover': { color: 'var(--text-primary)' },
              }}
            >
              <RefreshIcon sx={{ fontSize: 18 }} />
            </IconButton>
          )}
        </Box>
        {/* Status filter chips */}
        <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
          {STATUS_FILTER_OPTIONS.map((opt) => {
            const active = statusFilter === opt.value;
            return (
              <Box
                key={opt.value}
                onClick={() => setStatusFilter(opt.value)}
                sx={{
                  px: 1.25,
                  py: 0.25,
                  borderRadius: 1,
                  border: `1px solid ${active ? opt.color : 'var(--border)'}`,
                  bgcolor: active ? `${opt.color}22` : 'transparent',
                  cursor: 'pointer',
                  userSelect: 'none',
                  transition: 'all 0.15s ease',
                  '&:hover': { borderColor: opt.color },
                }}
              >
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    fontWeight: active ? FONT_WEIGHTS.WEIGHT_600 : FONT_WEIGHTS.WEIGHT_400,
                    color: active ? opt.color : 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  {opt.label}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>

      {/* Latest Actions collapsible */}
      {latestFiles.length > 0 && (
        <Box sx={{ borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          {/* Toggle row */}
          <Box
            onClick={() =>
              setLatestOpen((o) => {
                const next = !o;
                if (next && latestFiles.length === 1) setExpandedFile(latestFiles[0].name);
                return next;
              })
            }
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              px: 2,
              py: 0.875,
              cursor: 'pointer',
              userSelect: 'none',
              '&:hover': { bgcolor: 'var(--bg-tertiary)' },
            }}
          >
            {latestOpen ? (
              <ExpandLessIcon sx={{ fontSize: 16, color: 'var(--text-secondary)' }} />
            ) : (
              <ExpandMoreIcon sx={{ fontSize: 16, color: 'var(--text-secondary)' }} />
            )}
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                fontWeight: FONT_WEIGHTS.WEIGHT_600,
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Latest Actions
            </Typography>
            <Box
              sx={{
                ml: 0.5,
                px: 0.75,
                py: 0.1,
                borderRadius: 1,
                bgcolor: 'var(--bg-tertiary)',
                border: '1px solid var(--border)',
              }}
            >
              <Typography sx={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                {latestFiles.length}
              </Typography>
            </Box>
          </Box>

          <Collapse in={latestOpen}>
            <Box sx={{ bgcolor: 'var(--bg-primary)' }}>
              {latestFiles.map((file) => {
                const isOpen = expandedFile === file.name;
                // Pretty label: strip "latest_" prefix and ".log" suffix
                const label = file.name.replace(/^latest_/, '').replace(/\.log$/, '');
                return (
                  <Box key={file.name}>
                    {/* File row */}
                    <Box
                      onClick={() => setExpandedFile(isOpen ? null : file.name)}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.75,
                        px: 2.5,
                        py: 0.75,
                        cursor: 'pointer',
                        borderTop: '1px solid var(--border)',
                        '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                      }}
                    >
                      {isOpen ? (
                        <ExpandLessIcon
                          sx={{
                            fontSize: 14,
                            color: 'var(--text-secondary)',
                          }}
                        />
                      ) : (
                        <ExpandMoreIcon
                          sx={{
                            fontSize: 14,
                            color: 'var(--text-secondary)',
                          }}
                        />
                      )}
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.XS,
                          color: 'var(--text-primary)',
                          fontFamily: 'monospace',
                        }}
                      >
                        {label}
                      </Typography>
                    </Box>

                    {/* Log viewer */}
                    <Collapse in={isOpen}>
                      <Box
                        sx={{
                          height: 300,
                          borderTop: '1px solid var(--border)',
                        }}
                      >
                        <StreamLogViewer
                          logFileUrl={file.logUrl}
                          showHeader={false}
                          showLevelFilter={false}
                          maxHeight={300}
                          paginated
                          pageSize={100}
                        />
                      </Box>
                    </Collapse>
                  </Box>
                );
              })}
            </Box>
          </Collapse>
        </Box>
      )}

      {/* Cards list */}
      <Box sx={{ flex: 1, overflow: 'auto', px: 2, py: 1 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={24} sx={{ color: 'var(--text-secondary)' }} />
          </Box>
        ) : filteredEntries.length === 0 ? (
          <Box sx={{ py: 4, textAlign: 'center' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
              No executions found for the selected date range
            </Typography>
          </Box>
        ) : (
          groupedEntries.map((group, groupIdx) => {
            const isMulti = group.entries.length > 1;

            return (
              <Box key={`group-${group.logical_date}-${groupIdx}`} sx={{ mb: 2 }}>
                {/* Group background wraps both timeline col + cards for multi-run */}
                <Box
                  sx={{
                    ...(isMulti && {
                      border: '1px solid var(--border)',
                      borderRadius: 2,
                      bgcolor: 'var(--bg-tertiary)',
                      p: 1,
                    }),
                  }}
                >
                  {isMulti && (
                    <Typography
                      sx={{
                        fontSize: '0.65rem',
                        fontWeight: FONT_WEIGHTS.WEIGHT_600,
                        color: 'var(--text-secondary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        mb: 0.75,
                        px: 0.5,
                      }}
                    >
                      {group.entries.length} runs · same schedule slot
                    </Typography>
                  )}

                  {group.entries.map((entry, entryIdx) => {
                    const sc = STATUS_COLORS[entry.status] ?? STATUS_COLORS.pending;
                    const errMsg = getErrorMessage(entry);
                    const isLastInGroup = entryIdx === group.entries.length - 1;
                    return (
                      <Box
                        key={`${entry.session_id}-${entryIdx}`}
                        sx={{
                          display: 'flex',
                          gap: 2,
                          mb: isLastInGroup ? 0 : 1,
                        }}
                      >
                        {/* Timeline column — 1 dot per entry */}
                        <Box
                          sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            width: 80,
                            flexShrink: 0,
                            pt: 0.5,
                          }}
                        >
                          {entryIdx === 0 ? (
                            <>
                              <Typography
                                sx={{
                                  fontSize: FONT_SIZES.XS,
                                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                                  color: 'var(--text-primary)',
                                  fontFamily: 'monospace',
                                  textAlign: 'center',
                                  lineHeight: 1.3,
                                }}
                              >
                                {formatLogicalDate(group.logical_date)}
                              </Typography>
                              <Typography
                                sx={{
                                  fontSize: '0.65rem',
                                  color: 'var(--text-secondary)',
                                  fontFamily: 'monospace',
                                  textAlign: 'center',
                                  mt: 0.25,
                                }}
                              >
                                {formatLogicalTime(group.logical_date)}
                              </Typography>
                            </>
                          ) : (
                            <Box sx={{ height: 34 }} />
                          )}
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              borderRadius: '50%',
                              bgcolor: sc.dot,
                              mt: 0.75,
                              flexShrink: 0,
                            }}
                          />
                          {/* Line: within group connect entries; after group connect to next group */}
                          {(!isLastInGroup || groupIdx < groupedEntries.length - 1) && (
                            <Box
                              sx={{
                                width: 2,
                                flex: 1,
                                bgcolor: 'var(--border)',
                                mt: 0.5,
                              }}
                            />
                          )}
                        </Box>

                        {/* Card */}
                        <Box
                          onClick={() => onSessionClick(entry.session_id, entry._date)}
                          sx={{
                            flex: 1,
                            cursor: 'pointer',
                            '&:hover .history-card': {
                              borderColor: 'var(--accent)',
                            },
                          }}
                        >
                          <Box
                            className="history-card"
                            sx={{
                              border: '1px solid var(--border)',
                              borderRadius: 2,
                              bgcolor: 'var(--bg-secondary)',
                              overflow: 'hidden',
                              transition: 'border-color 0.2s ease',
                            }}
                          >
                            {/* Card header */}
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                px: 2,
                                py: 1,
                              }}
                            >
                              <Typography
                                sx={{
                                  fontSize: FONT_SIZES.BASE,
                                  fontWeight: FONT_WEIGHTS.BOLD,
                                  color: 'var(--text-primary)',
                                }}
                              >
                                Session #{entry.session_id?.substring(0, 5) ?? 'N/A'}
                              </Typography>
                              <Box
                                sx={{
                                  px: 1,
                                  py: 0.25,
                                  borderRadius: 1,
                                  bgcolor: sc.badgeBg,
                                  flexShrink: 0,
                                }}
                              >
                                <Typography
                                  sx={{
                                    fontSize: FONT_SIZES.XS,
                                    fontWeight: FONT_WEIGHTS.BOLD,
                                    color: sc.badge,
                                    textTransform: 'uppercase',
                                  }}
                                >
                                  {entry.status}
                                </Typography>
                              </Box>
                            </Box>

                            {/* Metadata grid */}
                            <Box
                              sx={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(4, 1fr)',
                                gap: 1,
                                px: 2,
                                py: 1,
                                borderTop: '1px solid var(--border)',
                              }}
                            >
                              {[
                                {
                                  label: 'Start Time',
                                  value: formatTime(entry.start_time),
                                },
                                {
                                  label: 'Duration',
                                  value: formatDuration(entry.duration_seconds),
                                },
                                {
                                  label: 'Frequency',
                                  value: entry.frequency ?? 'N/A',
                                },
                                {
                                  label: 'Retry #',
                                  value: String(entry.retry_number ?? 0),
                                },
                              ].map(({ label, value }) => (
                                <Box key={label}>
                                  <Typography
                                    sx={{
                                      fontSize: '0.65rem',
                                      color: 'var(--text-secondary)',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em',
                                      mb: 0.25,
                                    }}
                                  >
                                    {label}
                                  </Typography>
                                  <Typography
                                    sx={{
                                      fontSize: FONT_SIZES.XS,
                                      color: 'var(--text-primary)',
                                      fontFamily: 'monospace',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap',
                                    }}
                                  >
                                    {value}
                                  </Typography>
                                </Box>
                              ))}
                            </Box>

                            {/* Error message */}
                            {errMsg && (
                              <Box
                                sx={{
                                  mx: 2,
                                  mb: 1.5,
                                  p: 1.5,
                                  bgcolor: COLORS.RED_BG_SOFT,
                                  borderRadius: 1,
                                  border: `1px solid ${COLORS.RED_BORDER}`,
                                }}
                              >
                                <Typography
                                  sx={{
                                    fontSize: FONT_SIZES.XS,
                                    color: COLORS.RED,
                                    fontFamily: 'monospace',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                  }}
                                >
                                  {errMsg}
                                </Typography>
                              </Box>
                            )}
                          </Box>
                          {/* history-card */}
                        </Box>
                        {/* onClick wrapper */}
                      </Box>
                    );
                  })}
                </Box>
              </Box>
            );
          })
        )}
      </Box>

      {/* Footer */}
      <Box
        sx={{
          px: 2,
          py: 0.75,
          borderTop: '1px solid var(--border)',
          bgcolor: 'var(--bg-tertiary)',
          flexShrink: 0,
        }}
      >
        <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
          {filteredEntries.length}
          {statusFilter !== 'all' && ` of ${entries.length}`} execution
          {filteredEntries.length !== 1 ? 's' : ''}
        </Typography>
      </Box>
    </Box>
  );
}
