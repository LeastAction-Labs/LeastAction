/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, IconButton, Tooltip, Typography } from '@mui/material';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { formatDateTimeShort } from '@/utils/timeFormat';

import type { KpiData, StreakData } from '../../services/analyticsUtils';

interface KpiCardsProps {
  data: KpiData;
  maxFailStreak?: StreakData | null;
  maxSuccessStreak?: number;
}

const cardSx = {
  p: 2,
  borderRadius: BORDER_RADIUS.LG,
  bgcolor: 'var(--bg-secondary)',
  border: 1,
  borderColor: 'var(--border)',
  textAlign: 'center' as const,
  minWidth: 0,
};

interface KpiItem {
  label: string;
  value: string;
  color?: string;
}

function formatTime(isoStr: string): string {
  return formatDateTimeShort(isoStr);
}

export default function KpiCards({ data, maxFailStreak, maxSuccessStreak = 0 }: KpiCardsProps) {
  const items: KpiItem[] = [
    { label: 'Total Executions', value: String(data.totalExecutions) },
    { label: 'Success Rate', value: `${data.successRate.toFixed(1)}%`, color: COLORS.GREEN },
    {
      label: 'Failures',
      value: String(data.failCount),
      color: data.failCount > 0 ? COLORS.RED : undefined,
    },
    { label: 'Avg Duration', value: data.avgDurationFormatted },
    { label: 'Min Duration', value: data.minDurationFormatted },
    { label: 'Max Duration', value: data.maxDurationFormatted },
    { label: 'Median Duration', value: data.medianDurationFormatted },
    {
      label: 'Retry Rate',
      value: `${data.retryRate.toFixed(1)}%`,
      color: data.retryRate > 0 ? COLORS.AMBER : undefined,
    },
    { label: 'Avg Lag', value: data.avgLagFormatted },
  ];

  const failStreakTooltip = maxFailStreak
    ? `${formatTime(maxFailStreak.startTime)} → ${formatTime(maxFailStreak.endTime)}`
    : '';

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 1.5,
      }}
    >
      {items.map((item) => (
        <Box key={item.label} sx={cardSx}>
          <Typography
            sx={{
              fontSize: FONT_SIZES.XL,
              fontWeight: FONT_WEIGHTS.BOLD,
              color: item.color || 'var(--text-primary)',
              fontFamily: 'monospace',
              lineHeight: 1.2,
            }}
          >
            {item.value}
          </Typography>
          <Typography
            sx={{
              fontSize: FONT_SIZES.XXS,
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              mt: 0.5,
            }}
          >
            {item.label}
          </Typography>
        </Box>
      ))}

      {/* Max failure streak card */}
      <Box sx={{ ...cardSx, position: 'relative' }}>
        {maxFailStreak && (
          <Tooltip title={failStreakTooltip} placement="top" arrow>
            <IconButton
              size="small"
              sx={{
                position: 'absolute',
                top: 4,
                right: 4,
                p: 0.25,
                color: 'var(--text-secondary)',
                '&:hover': { color: 'var(--text-primary)' },
              }}
            >
              <InfoOutlinedIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        )}
        <Typography
          sx={{
            fontSize: FONT_SIZES.XL,
            fontWeight: FONT_WEIGHTS.BOLD,
            color: maxFailStreak ? COLORS.RED : COLORS.GREEN,
            fontFamily: 'monospace',
            lineHeight: 1.2,
          }}
        >
          {maxFailStreak ? `🔴 ${maxFailStreak.length}` : '🟢 0'}
        </Typography>
        <Typography
          sx={{
            fontSize: FONT_SIZES.XXS,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            mt: 0.5,
          }}
        >
          Max Failure Streak
        </Typography>
      </Box>

      {/* Max success streak card */}
      <Box sx={cardSx}>
        <Typography
          sx={{
            fontSize: FONT_SIZES.XL,
            fontWeight: FONT_WEIGHTS.BOLD,
            color: maxSuccessStreak > 0 ? COLORS.GREEN : 'var(--text-primary)',
            fontFamily: 'monospace',
            lineHeight: 1.2,
          }}
        >
          {maxSuccessStreak}
        </Typography>
        <Typography
          sx={{
            fontSize: FONT_SIZES.XXS,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            mt: 0.5,
          }}
        >
          Max Success Streak
        </Typography>
      </Box>
    </Box>
  );
}
