/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';

import type { ExecutionsOverTimeData, TimeGranularity } from '../../services/analyticsUtils';

interface ExecutionsOverTimeProps {
  data: ExecutionsOverTimeData;
  granularity: TimeGranularity;
  onGranularityChange: (g: TimeGranularity) => void;
}

const GRANULARITY_OPTIONS: { value: TimeGranularity; label: string }[] = [
  { value: '30min', label: '30m' },
  { value: 'hour', label: '1h' },
  { value: '12hour', label: '12h' },
  { value: 'day', label: '24h' },
  { value: 'week', label: '1w' },
  { value: 'month', label: '1M' },
];

function shortenLabel(label: string, granularity: TimeGranularity): string {
  switch (granularity) {
    case '30min':
    case 'hour':
      return label.split(' ')[1] || label;
    case '12hour':
      return label.replace(' 00:00', ' AM').replace(' 12:00', ' PM');
    case 'week':
      return label; // "W 2026-03-23"
    case 'month':
      return label; // "2026-03"
    default:
      return label;
  }
}

export default function ExecutionsOverTime({
  data,
  granularity,
  onGranularityChange,
}: ExecutionsOverTimeProps) {
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
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
          No execution data for this period
        </Typography>
      </Box>
    );
  }

  const shortLabels = data.labels.map((l) => shortenLabel(l, granularity));
  const maxCount = Math.max(
    ...data.successCounts.map((v, i) => v + data.errorCounts[i] + data.otherCounts[i]),
  );

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
          Executions Over Time
        </Typography>
        <ToggleButtonGroup
          value={granularity}
          exclusive
          onChange={(_, val) => {
            if (val) onGranularityChange(val);
          }}
          size="small"
          sx={{
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
          }}
        >
          {GRANULARITY_OPTIONS.map((opt) => (
            <ToggleButton key={opt.value} value={opt.value}>
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
      <BarChart
        xAxis={[
          {
            scaleType: 'band',
            data: shortLabels,
            tickLabelStyle: {
              fontSize: 10,
              angle: -45,
              textAnchor: 'end',
              fill: 'var(--text-primary)',
            },
          },
        ]}
        yAxis={[
          {
            tickMinStep: 1,
            max: maxCount < 5 ? maxCount + 1 : undefined,
            label: 'Executions',
            labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
            tickLabelStyle: { fill: 'var(--text-primary)', fontSize: 10 },
          },
        ]}
        series={[
          {
            data: data.successCounts,
            stack: 'status',
            label: 'Success',
            color: COLORS.GREEN,
          },
          { data: data.errorCounts, stack: 'status', label: 'Error', color: COLORS.RED },
          { data: data.otherCounts, stack: 'status', label: 'Other', color: COLORS.BLUE },
        ]}
        height={300}
        margin={{ bottom: 60, left: 55, right: 20, top: 20 }}
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
