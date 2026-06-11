/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';
import { DataGrid, type GridColDef, type GridRenderCellParams } from '@mui/x-data-grid';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { STATUS_COLORS } from '@/constants/logConstants';
import type { TaskHistoryEntry } from '@/hooks/useTaskHistory';
import { formatDateTimeFull } from '@/utils/timeFormat';

import { extractErrorMessage } from '../../services/analyticsUtils';

interface ExecutionLogTableProps {
  entries: TaskHistoryEntry[];
  onSessionClick?: (sessionId: string, date: string) => void;
}

function formatTime(isoStr: string): string {
  return formatDateTimeFull(isoStr);
}

function formatDuration(seconds: number): string {
  if (seconds == null || isNaN(seconds)) return 'N/A';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function getRawOutputText(entry: TaskHistoryEntry): string {
  if (!entry.output) return '';
  try {
    return JSON.stringify(entry.output, null, 2);
  } catch {
    return String(entry.output);
  }
}

export default function ExecutionLogTable({ entries, onSessionClick }: ExecutionLogTableProps) {
  const columns: GridColDef[] = [
    {
      field: 'start_time',
      headerName: 'Timestamp',
      flex: 1,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams) => {
        const row = params.row;
        const hasLink = onSessionClick && row._sessionId;
        return (
          <Typography
            onClick={
              hasLink
                ? (e: React.MouseEvent) => {
                    e.stopPropagation();
                    onSessionClick(row._sessionId, row._date);
                  }
                : undefined
            }
            sx={{
              fontSize: FONT_SIZES.XXS,
              fontFamily: 'monospace',
              color: hasLink ? COLORS.BLUE : 'var(--text-primary)',
              cursor: hasLink ? 'pointer' : 'default',
              textDecoration: hasLink ? 'underline' : 'none',
              '&:hover': hasLink ? { color: '#2563eb' } : {},
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {formatTime(params.value)}
          </Typography>
        );
      },
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 100,
      renderCell: (params: GridRenderCellParams) => {
        const sc = STATUS_COLORS[params.value] ?? STATUS_COLORS.pending;
        return (
          <Box
            sx={{
              px: 1,
              py: 0.25,
              borderRadius: 1,
              bgcolor: sc.badgeBg,
              display: 'inline-block',
            }}
          >
            <Typography
              sx={{
                fontSize: FONT_SIZES.XXS,
                fontWeight: FONT_WEIGHTS.BOLD,
                color: sc.badge,
                textTransform: 'uppercase',
              }}
            >
              {params.value}
            </Typography>
          </Box>
        );
      },
    },
    {
      field: 'duration_seconds',
      headerName: 'Duration',
      width: 90,
      valueFormatter: (value: number) => formatDuration(value),
    },
    {
      field: 'retry_number',
      headerName: 'Retry #',
      width: 70,
      type: 'number',
    },
    {
      field: 'error_output',
      headerName: 'Output',
      flex: 2.5,
      minWidth: 250,
      renderCell: (params: GridRenderCellParams) => {
        const errMsg = params.row._errorMessage;
        const rawOutput = params.row._rawOutput;
        const displayText = errMsg || rawOutput || '-';
        return (
          <Box sx={{ overflow: 'hidden', width: '100%' }}>
            <Typography
              title={displayText}
              sx={{
                fontSize: FONT_SIZES.XXS,
                fontFamily: 'monospace',
                color: errMsg ? COLORS.RED : 'var(--text-secondary)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {displayText}
            </Typography>
          </Box>
        );
      },
    },
  ];

  const rows = entries.map((e, idx) => {
    const errMsg = extractErrorMessage(e);
    const rawOutput = getRawOutputText(e);
    return {
      id: `${e.session_id ?? idx}-${idx}`,
      start_time: e.start_time,
      status: e.status,
      duration_seconds: e.duration_seconds,
      retry_number: e.retry_number ?? 0,
      error_output: errMsg || rawOutput || '',
      _errorMessage: errMsg,
      _rawOutput: rawOutput,
      _sessionId: e.session_id,
      _date: e._date,
    };
  });

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
        Execution Log ({entries.length} runs)
      </Typography>

      {entries.length === 0 ? (
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
          No executions found
        </Typography>
      ) : (
        <Box
          sx={{
            '& .MuiDataGrid-root': {
              border: '1px solid var(--border)',
              bgcolor: 'var(--bg-primary)',
              fontSize: FONT_SIZES.XXS,
            },
            '& .MuiDataGrid-columnHeaders': {
              bgcolor: 'var(--bg-tertiary)',
              borderBottom: '1px solid var(--border)',
            },
            '& .MuiDataGrid-columnHeaderTitle': {
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
              fontSize: FONT_SIZES.XXS,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--text-secondary)',
            },
            '& .MuiDataGrid-cell': {
              borderBottom: '1px solid var(--border)',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
              fontSize: FONT_SIZES.XXS,
            },
            '& .MuiDataGrid-row:hover': {
              bgcolor: 'var(--bg-tertiary)',
            },
            '& .MuiDataGrid-footerContainer': {
              borderTop: '1px solid var(--border)',
              bgcolor: 'var(--bg-tertiary)',
            },
            '& .MuiTablePagination-root': {
              color: 'var(--text-secondary)',
              fontSize: FONT_SIZES.XXS,
            },
          }}
        >
          <DataGrid
            rows={rows}
            columns={columns}
            autoHeight
            hideFooter
            initialState={{
              sorting: { sortModel: [{ field: 'start_time', sort: 'desc' }] },
            }}
            disableRowSelectionOnClick
            density="compact"
          />
        </Box>
      )}
    </Box>
  );
}
