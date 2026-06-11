/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';

import type { DurationTrendData } from '../../services/analyticsUtils';

interface DurationTrendsProps {
  data: DurationTrendData;
}

export default function DurationTrends({ data }: DurationTrendsProps) {
  if (data.durations.length === 0) {
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
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
          No duration data available
        </Typography>
      </Box>
    );
  }

  const indices = data.durations.map((_, i) => i);

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
        Duration Trends
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, mb: 1, flexWrap: 'wrap' }}>
        <Typography sx={{ fontSize: FONT_SIZES.XXS, color: 'var(--text-secondary)' }}>
          Avg: <strong>{data.mean.toFixed(1)}s</strong>
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.XXS, color: 'var(--text-secondary)' }}>
          +1&sigma;: <strong>{data.stdDevPlus.toFixed(1)}s</strong>
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.XXS, color: 'var(--text-secondary)' }}>
          -1&sigma;: <strong>{data.stdDevMinus.toFixed(1)}s</strong>
        </Typography>
      </Box>
      <LineChart
        xAxis={[
          {
            data: indices,
            scaleType: 'linear',
            label: 'Execution #',
            labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
            tickLabelStyle: { fill: 'var(--text-primary)', fontSize: 10 },
            tickMinStep: 1,
          },
        ]}
        yAxis={[
          {
            min: 0,
            label: 'Duration (s)',
            labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
            tickLabelStyle: { fill: 'var(--text-primary)', fontSize: 10 },
          },
        ]}
        series={[
          {
            data: data.durations,
            label: 'Duration (s)',
            color: '#667eea',
            showMark: data.durations.length <= 50,
          },
          {
            data: data.durations.map(() => data.mean),
            label: 'Avg (s)',
            color: COLORS.AMBER,
            showMark: false,
          },
          {
            data: data.durations.map(() => data.stdDevPlus),
            label: '+1σ (s)',
            color: COLORS.RED,
            showMark: false,
          },
          {
            data: data.durations.map(() => data.stdDevMinus),
            label: '-1σ (s)',
            color: COLORS.RED,
            showMark: false,
          },
        ]}
        height={300}
        margin={{ left: 55, right: 20, top: 20, bottom: 40 }}
        slotProps={{
          legend: {
            position: { vertical: 'top', horizontal: 'end' },
          },
        }}
        sx={{ '& .MuiChartsLegend-label': { fill: 'var(--text-primary) !important' } }}
      />
    </Box>
  );
}
