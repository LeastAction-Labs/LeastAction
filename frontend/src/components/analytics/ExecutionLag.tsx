/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';
import { LineChart } from '@mui/x-charts/LineChart';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';

import type { ExecutionLagData } from '../../services/analyticsUtils';

interface ExecutionLagProps {
  lagData: ExecutionLagData;
}

export default function ExecutionLag({ lagData }: ExecutionLagProps) {
  if (lagData.lagSeconds.length === 0) {
    return (
      <Box
        sx={{
          p: 2.5,
          borderRadius: BORDER_RADIUS.LG,
          bgcolor: 'var(--bg-secondary)',
          border: 1,
          borderColor: 'var(--border)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          minHeight: 200,
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
          Execution Lag
        </Typography>
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
            Not enough data
          </Typography>
        </Box>
      </Box>
    );
  }

  // Short labels: keep only HH:MM from "YYYY-MM-DD HH:MM"
  const shortLabels = lagData.labels.map((l) => l.split(' ')[1] || l);

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
        Execution Lag
      </Typography>

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
        Lag Per Execution (seconds after scheduled time)
      </Typography>
      <LineChart
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
            label: 'Lag (s)',
            labelStyle: { fill: 'var(--text-secondary)', fontSize: 11 },
            tickLabelStyle: { fill: 'var(--text-primary)', fontSize: 10 },
          },
        ]}
        series={[
          {
            data: lagData.lagSeconds,
            label: 'Lag (s)',
            color: '#667eea',
            showMark: lagData.lagSeconds.length <= 50,
          },
        ]}
        height={280}
        margin={{ left: 55, right: 20, top: 20, bottom: 60 }}
        sx={{ '& .MuiChartsLegend-label': { fill: 'var(--text-primary) !important' } }}
      />
    </Box>
  );
}
