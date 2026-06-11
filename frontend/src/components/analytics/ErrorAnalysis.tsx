/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import type { TaskHistoryEntry } from '@/hooks/useTaskHistory';
import { formatDateTimeShort } from '@/utils/timeFormat';

import { computeErrorFrequency, computeErrorList } from '../../services/analyticsUtils';

interface ErrorAnalysisProps {
  entries: TaskHistoryEntry[];
  onSessionClick?: (sessionId: string) => void;
}

const TOP_N_OPTIONS = [5, 10, 20] as const;
type TopN = (typeof TOP_N_OPTIONS)[number];

function formatTime(isoStr: string): string {
  return formatDateTimeShort(isoStr);
}

function formatLogicalDate(s: string): string {
  if (!s || s === 'N/A') return 'N/A';
  return s.split(/[T ]/)[0];
}

const toggleSx = {
  '& .MuiToggleButton-root': {
    fontSize: FONT_SIZES.XXS,
    px: 1,
    py: 0.25,
    color: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    textTransform: 'none',
    '&.Mui-selected': {
      bgcolor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontWeight: FONT_WEIGHTS.WEIGHT_600,
    },
  },
} as const;

export default function ErrorAnalysis({ entries, onSessionClick }: ErrorAnalysisProps) {
  const [topN, setTopN] = useState<TopN>(10);

  const frequency = computeErrorFrequency(entries, topN);
  const errorList = computeErrorList(entries);
  const hasErrors = frequency.length > 0 || errorList.length > 0;

  return (
    <Box
      sx={{
        p: 2.5,
        borderRadius: BORDER_RADIUS.LG,
        bgcolor: 'var(--bg-secondary)',
        border: 1,
        borderColor: 'var(--border)',
      }}
    >
      <Typography
        sx={{
          fontSize: FONT_SIZES.SM,
          fontWeight: FONT_WEIGHTS.BOLD,
          color: 'var(--text-primary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          mb: 2,
        }}
      >
        Error Analysis
      </Typography>

      {!hasErrors ? (
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: COLORS.GREEN }}>
          No errors in this period
        </Typography>
      ) : (
        <>
          {/* Error frequency bar chart */}
          {frequency.length > 0 && (
            <Box sx={{ mb: 3 }}>
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
                    fontSize: FONT_SIZES.XS,
                    fontWeight: FONT_WEIGHTS.WEIGHT_600,
                    color: 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Most Frequent Errors
                </Typography>
                <ToggleButtonGroup
                  value={topN}
                  exclusive
                  onChange={(_, val) => {
                    if (val) setTopN(val);
                  }}
                  size="small"
                  sx={toggleSx}
                >
                  {TOP_N_OPTIONS.map((n) => (
                    <ToggleButton key={n} value={n}>
                      Top {n}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </Box>
              <BarChart
                yAxis={[
                  {
                    scaleType: 'band',
                    data: frequency.map((f) =>
                      f.message.length > 80 ? f.message.substring(0, 80) + '...' : f.message,
                    ),
                    tickLabelStyle: {
                      fontSize: 10,
                      fill: 'var(--text-primary)',
                    },
                  },
                ]}
                xAxis={[
                  {
                    label: 'Occurrences',
                    tickMinStep: 1,
                    labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
                    tickLabelStyle: {
                      fill: 'var(--text-primary)',
                      fontSize: 10,
                    },
                  },
                ]}
                series={[
                  {
                    data: frequency.map((f) => f.count),
                    label: 'Occurrences',
                    color: COLORS.RED,
                  },
                ]}
                layout="horizontal"
                height={Math.max(200, frequency.length * 50)}
                margin={{ left: 300, right: 20, top: 20, bottom: 40 }}
                sx={{
                  '& .MuiChartsLegend-label': {
                    fill: 'var(--text-primary) !important',
                  },
                }}
              />
            </Box>
          )}

          {/* Error list table */}
          {errorList.length > 0 && (
            <Box>
              <Typography
                sx={{
                  fontSize: FONT_SIZES.XS,
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                  color: 'var(--text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  mb: 1,
                }}
              >
                Error Log ({errorList.length} failures)
              </Typography>
              <Box
                sx={{
                  maxHeight: 300,
                  overflow: 'auto',
                  border: 1,
                  borderColor: 'var(--border)',
                  borderRadius: 1,
                }}
              >
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      {['Logical Date', 'Timestamp', 'Retry #', 'Error'].map((h) => (
                        <TableCell
                          key={h}
                          sx={{
                            bgcolor: 'var(--bg-tertiary)',
                            color: 'var(--text-secondary)',
                            fontSize: FONT_SIZES.XXS,
                            fontWeight: FONT_WEIGHTS.WEIGHT_600,
                            borderBottom: '1px solid var(--border)',
                          }}
                        >
                          {h}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {errorList.map((item, idx) => (
                      <TableRow
                        key={`${item.sessionId}-${idx}`}
                        sx={{
                          '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                        }}
                      >
                        <TableCell
                          sx={{
                            color: 'var(--text-primary)',
                            fontSize: FONT_SIZES.XXS,
                            fontFamily: 'monospace',
                            borderBottom: '1px solid var(--border)',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {formatLogicalDate(item.logicalDate)}
                        </TableCell>
                        <TableCell
                          sx={{
                            fontSize: FONT_SIZES.XXS,
                            fontFamily: 'monospace',
                            borderBottom: '1px solid var(--border)',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          <Typography
                            onClick={
                              onSessionClick && item.sessionId
                                ? () => onSessionClick(item.sessionId)
                                : undefined
                            }
                            sx={{
                              fontSize: FONT_SIZES.XXS,
                              fontFamily: 'monospace',
                              color:
                                onSessionClick && item.sessionId
                                  ? '#3b82f6'
                                  : 'var(--text-primary)',
                              cursor: onSessionClick && item.sessionId ? 'pointer' : 'default',
                              textDecoration:
                                onSessionClick && item.sessionId ? 'underline' : 'none',
                              '&:hover':
                                onSessionClick && item.sessionId ? { color: '#2563eb' } : {},
                            }}
                          >
                            {formatTime(item.startTime)}
                          </Typography>
                        </TableCell>
                        <TableCell
                          sx={{
                            color: 'var(--text-primary)',
                            fontSize: FONT_SIZES.XXS,
                            fontFamily: 'monospace',
                            borderBottom: '1px solid var(--border)',
                            textAlign: 'center',
                          }}
                        >
                          {item.retryNumber}
                        </TableCell>
                        <TableCell
                          sx={{
                            color: COLORS.RED,
                            fontSize: FONT_SIZES.XXS,
                            fontFamily: 'monospace',
                            borderBottom: '1px solid var(--border)',
                            maxWidth: 400,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.errorMessage}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </Box>
          )}
        </>
      )}
    </Box>
  );
}
