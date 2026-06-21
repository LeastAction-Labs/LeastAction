/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import { Box, CircularProgress, Tooltip, Typography } from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { STATUS_COLORS } from '@/constants/logConstants';
import { useRecentRuns } from '@/hooks/useRecentRuns';
import { formatDateOnly } from '@/utils/timeFormat';

const RECENT_RUNS_LIMIT = 15;

export interface RecentRunsStripProps {
  taskLaui: string;
  /** Called when a run box is clicked, with that run's session id. */
  onRunClick: (sessionId: string) => void;
  /** Changing this forces the strip to re-fetch (e.g. on table refresh). */
  refreshKey?: number;
}

/**
 * An Airflow-grid-style horizontal strip of a task's most recent runs, rendered
 * inside a dense table cell. Each box is colored by run status; hovering shows
 * the run's logical date and clicking opens that run's logs. Fetching is
 * deferred until the strip scrolls into view.
 */
export default function RecentRunsStrip({
  taskLaui,
  onRunClick,
  refreshKey = 0,
}: RecentRunsStripProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || inView) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '100px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [inView]);

  const { runs, loading } = useRecentRuns(taskLaui, RECENT_RUNS_LIMIT, inView, refreshKey);

  return (
    <Box
      ref={containerRef}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.5,
        overflowX: 'auto',
        maxWidth: '100%',
        minHeight: 18,
        // Slim scrollbar that only hints when content overflows
        '&::-webkit-scrollbar': { height: 4 },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'var(--border)',
          borderRadius: 2,
        },
      }}
    >
      {loading && runs.length === 0 ? (
        <CircularProgress size={12} sx={{ color: 'var(--text-secondary)' }} />
      ) : runs.length === 0 ? (
        <Typography sx={{ fontSize: FONT_SIZES.XXS, color: 'var(--text-secondary)' }}>—</Typography>
      ) : (
        runs.map((run, idx) => {
          const color = (STATUS_COLORS[run.status] ?? STATUS_COLORS.pending).dot;
          const sessionId = run.session_id;
          return (
            <Tooltip
              key={`${sessionId ?? run.fileName}-${idx}`}
              arrow
              placement="top"
              title={
                <Box>
                  <Typography
                    sx={{ fontSize: FONT_SIZES.XXS, fontWeight: FONT_WEIGHTS.WEIGHT_600 }}
                  >
                    {formatDateOnly(run.logical_date)}
                  </Typography>
                  <Typography sx={{ fontSize: FONT_SIZES.XXS, textTransform: 'capitalize' }}>
                    {run.status}
                  </Typography>
                </Box>
              }
            >
              <Box
                onClick={(e) => {
                  e.stopPropagation();
                  if (sessionId) onRunClick(sessionId);
                }}
                sx={{
                  width: 12,
                  height: 16,
                  flexShrink: 0,
                  borderRadius: 0.5,
                  bgcolor: color,
                  cursor: sessionId ? 'pointer' : 'default',
                  opacity: 0.75,
                  transition: 'all 0.15s ease',
                  '&:hover': {
                    opacity: 1,
                    transform: 'scaleY(1.15)',
                  },
                }}
              />
            </Tooltip>
          );
        })
      )}
    </Box>
  );
}
