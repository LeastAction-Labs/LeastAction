/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useMemo, useState } from 'react';

import { Box, CircularProgress, Typography } from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { useTheme } from '@/contexts/ThemeContext';
import { parseDate, today, useTaskHistory } from '@/hooks/useTaskHistory';

import {
  type TimeGranularity,
  autoGranularity,
  computeConsecutiveFailureStreaks,
  computeDurationTrends,
  computeExecutionLag,
  computeExecutionsOverTime,
  computeKpis,
  computeMaxSuccessStreak,
} from '../../services/analyticsUtils';
import DurationHistogram from '../analytics/DurationHistogram';
import DurationTrends from '../analytics/DurationTrends';
import ErrorAnalysis from '../analytics/ErrorAnalysis';
import ExecutionLag from '../analytics/ExecutionLag';
import ExecutionsOverTime from '../analytics/ExecutionsOverTime';
import KpiCards from '../analytics/KpiCards';

interface TaskAnalyticsTabProps {
  taskLaui: string;
  logicalDate?: string;
  onNavigateToSession?: (sessionId: string) => void;
}

function yesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().split('T')[0];
}

export default function TaskAnalyticsTab({
  taskLaui,
  logicalDate,
  onNavigateToSession,
}: TaskAnalyticsTabProps) {
  const { theme } = useTheme();
  const defaultTo = logicalDate ? parseDate(logicalDate) : today();
  const defaultFrom = logicalDate ? parseDate(logicalDate) : yesterday();

  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(defaultTo);
  const [granularity, setGranularity] = useState<TimeGranularity>(() =>
    autoGranularity(defaultFrom, defaultTo),
  );
  const [startTimeFilter, setStartTimeFilter] = useState<Date | null>(null);

  const { entries, loading } = useTaskHistory(taskLaui, dateFrom, dateTo);

  const filteredEntries = useMemo(() => {
    if (!startTimeFilter) return entries;
    return entries.filter((e) => {
      const t = e.task_instance_start_date || e.start_time;
      return t && new Date(t) >= startTimeFilter;
    });
  }, [entries, startTimeFilter]);

  const kpis = useMemo(() => computeKpis(filteredEntries), [filteredEntries]);
  const executionsOverTime = useMemo(
    () => computeExecutionsOverTime(filteredEntries, granularity),
    [filteredEntries, granularity],
  );
  const durationTrends = useMemo(() => computeDurationTrends(filteredEntries), [filteredEntries]);
  const lagData = useMemo(() => computeExecutionLag(filteredEntries), [filteredEntries]);
  const failStreaks = useMemo(
    () => computeConsecutiveFailureStreaks(filteredEntries),
    [filteredEntries],
  );
  const maxSuccessStreak = useMemo(
    () => computeMaxSuccessStreak(filteredEntries),
    [filteredEntries],
  );

  const inputStyle = {
    padding: '6px 10px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    borderRadius: 6,
    fontSize: FONT_SIZES.XS,
    outline: 'none',
    colorScheme: theme === 'white' ? 'light' : 'dark',
    width: '100%',
    boxSizing: 'border-box' as const,
  } as const;

  return (
    <Box sx={{ height: '100%', overflow: 'auto', p: 2.5 }}>
      {/* Header with period presets + date range */}
      <Box
        sx={{
          display: 'flex',
          alignItems: { xs: 'flex-start', sm: 'center' },
          justifyContent: 'space-between',
          mb: 2.5,
          flexWrap: 'wrap',
          gap: 1.5,
        }}
      >
        <Typography
          sx={{
            fontSize: FONT_SIZES.LG,
            fontWeight: FONT_WEIGHTS.BOLD,
            color: 'var(--text-primary)',
            letterSpacing: '0.05em',
          }}
        >
          ANALYTICS
        </Typography>

        {/* Manual date range */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            flexWrap: 'wrap',
            flex: { xs: '1 1 100%', sm: '0 1 auto' },
          }}
        >
          <Typography
            sx={{
              fontSize: FONT_SIZES.XS,
              color: 'var(--text-secondary)',
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
            }}
          >
            From
          </Typography>
          <input
            type="date"
            value={dateFrom}
            max={dateTo}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setStartTimeFilter(null);
            }}
            style={{ ...inputStyle, flex: 1, minWidth: 120 }}
          />
          <Typography
            sx={{
              fontSize: FONT_SIZES.XS,
              color: 'var(--text-secondary)',
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
            }}
          >
            To
          </Typography>
          <input
            type="date"
            value={dateTo}
            min={dateFrom}
            onChange={(e) => {
              setDateTo(e.target.value);
              setStartTimeFilter(null);
            }}
            style={{ ...inputStyle, flex: 1, minWidth: 120 }}
          />
        </Box>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
          <CircularProgress size={32} sx={{ color: 'var(--text-secondary)' }} />
        </Box>
      ) : filteredEntries.length === 0 ? (
        <Box sx={{ py: 8, textAlign: 'center' }}>
          <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
            No executions found for the selected date range
          </Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          {/* KPI Cards */}
          <KpiCards
            data={kpis}
            maxFailStreak={failStreaks[0] ?? null}
            maxSuccessStreak={maxSuccessStreak}
          />

          {/* Two-column: Executions Over Time + Duration Trends */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
              gap: 2.5,
            }}
          >
            <ExecutionsOverTime
              data={executionsOverTime}
              granularity={granularity}
              onGranularityChange={setGranularity}
            />
            <DurationTrends data={durationTrends} />
          </Box>

          {/* Full-width: Error Analysis */}
          <ErrorAnalysis entries={filteredEntries} onSessionClick={onNavigateToSession} />

          {/* Two-column: Execution Lag + Duration Distribution */}
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
              gap: 2.5,
            }}
          >
            <ExecutionLag lagData={lagData} />
            <DurationHistogram entries={filteredEntries} />
          </Box>
        </Box>
      )}
    </Box>
  );
}
