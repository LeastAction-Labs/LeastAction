/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useMemo, useState } from 'react';

import { Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import type { TaskHistoryEntry } from '@/hooks/useTaskHistory';

import { computeDurationHistogram } from '../../services/analyticsUtils';

interface DurationHistogramProps {
  entries: TaskHistoryEntry[];
}

const BUCKET_OPTIONS = [5, 10, 20] as const;
type BucketCount = (typeof BUCKET_OPTIONS)[number];

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

export default function DurationHistogram({ entries }: DurationHistogramProps) {
  const [bucketCount, setBucketCount] = useState<BucketCount>(10);

  const data = useMemo(
    () => computeDurationHistogram(entries, bucketCount),
    [entries, bucketCount],
  );

  if (data.labels.length === 0) {
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
            mb: 1,
          }}
        >
          Duration Distribution
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
          No duration data available
        </Typography>
      </Box>
    );
  }

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
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Typography
          sx={{
            fontSize: FONT_SIZES.SM,
            fontWeight: FONT_WEIGHTS.BOLD,
            color: 'var(--text-primary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          Duration Distribution
        </Typography>
        <ToggleButtonGroup
          value={bucketCount}
          exclusive
          onChange={(_, val) => {
            if (val) setBucketCount(val);
          }}
          size="small"
          sx={toggleSx}
        >
          {BUCKET_OPTIONS.map((n) => (
            <ToggleButton key={n} value={n}>
              {n} buckets
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>

      <BarChart
        yAxis={[
          {
            scaleType: 'band',
            data: data.labels,
            tickLabelStyle: { fontSize: 10, fill: 'var(--text-primary)' },
          },
        ]}
        xAxis={[
          {
            label: 'Executions',
            tickMinStep: 1,
            labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
            tickLabelStyle: { fill: 'var(--text-primary)', fontSize: 10 },
          },
        ]}
        series={[{ data: data.counts, label: 'Executions', color: '#667eea' }]}
        layout="horizontal"
        height={Math.max(200, data.labels.length * 35)}
        margin={{ left: 130, right: 20, top: 20, bottom: 40 }}
        sx={{ '& .MuiChartsLegend-label': { fill: 'var(--text-primary) !important' } }}
      />
    </Box>
  );
}
