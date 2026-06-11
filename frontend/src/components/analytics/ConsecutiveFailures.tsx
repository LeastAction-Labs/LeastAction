/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';

import { BORDER_RADIUS, COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { formatDateTimeShort } from '@/utils/timeFormat';

import type { StreakData } from '../../services/analyticsUtils';

interface ConsecutiveFailuresProps {
  streaks: StreakData[];
}

function formatTime(isoStr: string): string {
  return formatDateTimeShort(isoStr);
}

export default function ConsecutiveFailures({ streaks }: ConsecutiveFailuresProps) {
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
        Failure Streaks
      </Typography>

      {streaks.length === 0 ? (
        <Typography sx={{ fontSize: FONT_SIZES.SM, color: COLORS.GREEN }}>
          No consecutive failure streaks detected
        </Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {streaks.map((s, i) => (
            <Box
              key={i}
              sx={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 1.5,
                p: 1.5,
                borderRadius: 1,
                bgcolor: 'var(--bg-primary)',
                border: 1,
                borderColor: 'var(--border)',
              }}
            >
              <Typography sx={{ fontSize: 16, lineHeight: 1.4 }}>🔴</Typography>
              <Box>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    fontWeight: FONT_WEIGHTS.BOLD,
                    color: COLORS.RED,
                  }}
                >
                  {i === 0 ? 'Max Failure Streak' : `Streak ${i + 1}`}
                </Typography>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    color: 'var(--text-primary)',
                    mt: 0.25,
                  }}
                >
                  {s.length} consecutive failure{s.length !== 1 ? 's' : ''}
                </Typography>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XXS,
                    color: 'var(--text-secondary)',
                    fontFamily: 'monospace',
                    mt: 0.25,
                  }}
                >
                  {formatTime(s.startTime)} →{' '}
                  {formatTime(s.endTime).split(' ')[1] || formatTime(s.endTime)}
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
