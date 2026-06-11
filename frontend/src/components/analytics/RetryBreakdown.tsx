/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';
import { BarChart } from '@mui/x-charts/BarChart';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';

import type { RetryDepthItem, RetryOutcomeData } from '../../services/analyticsUtils';

interface RetryBreakdownProps {
  depth: RetryDepthItem[];
  outcome: RetryOutcomeData;
}

export default function RetryBreakdown({ depth, outcome }: RetryBreakdownProps) {
  if (depth.length === 0) {
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
          Retry Breakdown
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
          No retry data available
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
        Retry Breakdown
      </Typography>

      {/* Retry depth distribution */}
      <Box sx={{ mb: 3 }}>
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
          Retry Depth Distribution
        </Typography>
        <BarChart
          xAxis={[{ scaleType: 'band', data: depth.map((d) => `Retry ${d.label}`) }]}
          series={[{ data: depth.map((d) => d.count), label: 'Executions', color: '#667eea' }]}
          height={220}
          margin={{ left: 40, right: 20, top: 20, bottom: 30 }}
        />
      </Box>

      {/* Retry outcome */}
      {outcome.labels.length > 0 && (
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
            Retry Outcome
          </Typography>
          <BarChart
            xAxis={[{ scaleType: 'band', data: outcome.labels }]}
            series={[
              {
                data: outcome.succeeded,
                stack: 'outcome',
                label: 'Succeeded',
                color: COLORS.GREEN,
              },
              {
                data: outcome.failed,
                stack: 'outcome',
                label: 'Still Failed',
                color: COLORS.RED,
              },
            ]}
            height={220}
            margin={{ left: 40, right: 20, top: 20, bottom: 30 }}
            slotProps={{
              legend: {
                position: { vertical: 'top', horizontal: 'end' },
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
}
