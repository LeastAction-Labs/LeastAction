/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { TaskHistoryEntry } from '@/hooks/useTaskHistory';

// ── Status helpers ───────────────────────────────────────────────────────────

export function isError(status: string): boolean {
  return ['error', 'failed', 'fail', 'timeout'].includes(status);
}

export function extractErrorMessage(entry: TaskHistoryEntry): string {
  // Check output.error regardless of status (status derivation may be imperfect)
  if (entry.output?.error) return String(entry.output.error);
  if (!isError(entry.status)) return '';
  const msg = entry.output?.run_output?.result?.message;
  if (typeof msg === 'string') return msg;
  if (entry.output?.message) return String(entry.output.message);
  return 'Unknown error';
}

// ── Math helpers ─────────────────────────────────────────────────────────────

export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function stdDev(values: number[]): number {
  if (values.length < 2) return 0;
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const sqDiffs = values.map((v) => (v - avg) ** 2);
  return Math.sqrt(sqDiffs.reduce((a, b) => a + b, 0) / values.length);
}

function formatDurationShort(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

// ── KPI ──────────────────────────────────────────────────────────────────────

export interface KpiData {
  totalExecutions: number;
  successRate: number;
  failCount: number;
  avgDuration: number;
  minDuration: number;
  maxDuration: number;
  medianDuration: number;
  retryRate: number;
  avgLagSeconds: number | null;
  avgDurationFormatted: string;
  minDurationFormatted: string;
  maxDurationFormatted: string;
  medianDurationFormatted: string;
  avgLagFormatted: string;
}

export function computeKpis(entries: TaskHistoryEntry[]): KpiData {
  const total = entries.length;
  const successCount = entries.filter((e) => e.status === 'success').length;
  const failCount = entries.filter((e) => isError(e.status)).length;
  const retryEntries = entries.filter((e) => e.retry_number > 0);
  const durations = entries.map((e) => e.duration_seconds).filter((d) => d != null && !isNaN(d));

  const avgDuration =
    durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
  const minDuration = durations.length > 0 ? Math.min(...durations) : 0;
  const maxDuration = durations.length > 0 ? Math.max(...durations) : 0;
  const medianDuration = median(durations);

  // Execution lag: task_instance_start_date[i] - next_run_date[i-1]
  // The previous run's next_run_date is the scheduled start time for the current run
  const sortedForLag = [...entries]
    .filter((e) => e.frequency !== 'ADHOC' && e.task_instance_start_date && e.next_run_date)
    .sort(
      (a, b) =>
        new Date(a.task_instance_start_date!).getTime() -
        new Date(b.task_instance_start_date!).getTime(),
    );
  const lags: number[] = [];
  for (let i = 1; i < sortedForLag.length; i++) {
    const instanceStart = new Date(sortedForLag[i].task_instance_start_date!).getTime();
    const scheduled = new Date(sortedForLag[i - 1].next_run_date!).getTime();
    if (!isNaN(instanceStart) && !isNaN(scheduled)) {
      lags.push((instanceStart - scheduled) / 1000);
    }
  }
  const avgLag = lags.length > 0 ? lags.reduce((a, b) => a + b, 0) / lags.length : null;

  return {
    totalExecutions: total,
    successRate: total > 0 ? (successCount / total) * 100 : 0,
    failCount,
    avgDuration,
    minDuration,
    maxDuration,
    medianDuration,
    retryRate: total > 0 ? (retryEntries.length / total) * 100 : 0,
    avgLagSeconds: avgLag,
    avgDurationFormatted: formatDurationShort(avgDuration),
    minDurationFormatted: formatDurationShort(minDuration),
    maxDurationFormatted: formatDurationShort(maxDuration),
    medianDurationFormatted: formatDurationShort(medianDuration),
    avgLagFormatted: avgLag != null ? formatDurationShort(avgLag) : 'N/A',
  };
}

// ── Executions Over Time ─────────────────────────────────────────────────────

export interface ExecutionsOverTimeData {
  labels: string[];
  successCounts: number[];
  errorCounts: number[];
  otherCounts: number[];
  successRates: number[];
}

export type TimeGranularity = '30min' | 'hour' | '12hour' | 'day' | 'week' | 'month';

function bucketKey(d: Date, granularity: TimeGranularity): string {
  const iso = d.toISOString().split('T')[0];
  const h = d.getUTCHours();
  const m = d.getUTCMinutes();
  switch (granularity) {
    case '30min': {
      const half = m < 30 ? '00' : '30';
      return `${iso} ${String(h).padStart(2, '0')}:${half}`;
    }
    case 'hour':
      return `${iso} ${String(h).padStart(2, '0')}:00`;
    case '12hour':
      return `${iso} ${h < 12 ? '00:00' : '12:00'}`;
    case 'day':
      return iso;
    case 'week': {
      // ISO week: floor to Monday
      const copy = new Date(d);
      const day = copy.getUTCDay();
      const diff = (day === 0 ? -6 : 1) - day;
      copy.setUTCDate(copy.getUTCDate() + diff);
      return `W ${copy.toISOString().split('T')[0]}`;
    }
    case 'month':
      return iso.substring(0, 7); // YYYY-MM
    default:
      return iso;
  }
}

export function computeExecutionsOverTime(
  entries: TaskHistoryEntry[],
  granularity: TimeGranularity,
): ExecutionsOverTimeData {
  const bucketMap = new Map<string, { success: number; error: number; other: number }>();

  for (const e of entries) {
    const runDate = e.task_instance_start_date || e.start_time;
    if (!runDate) continue;
    const d = new Date(runDate);
    const key = bucketKey(d, granularity);

    if (!bucketMap.has(key)) bucketMap.set(key, { success: 0, error: 0, other: 0 });
    const b = bucketMap.get(key)!;
    if (e.status === 'success') b.success++;
    else if (isError(e.status)) b.error++;
    else b.other++;
  }

  const sorted = [...bucketMap.entries()].sort(([a], [b]) => a.localeCompare(b));
  const labels = sorted.map(([k]) => k);
  const successCounts = sorted.map(([, v]) => v.success);
  const errorCounts = sorted.map(([, v]) => v.error);
  const otherCounts = sorted.map(([, v]) => v.other);
  const successRates = sorted.map(([, v]) => {
    const total = v.success + v.error + v.other;
    return total > 0 ? (v.success / total) * 100 : 0;
  });

  return { labels, successCounts, errorCounts, otherCounts, successRates };
}

// ── Duration Trends ──────────────────────────────────────────────────────────

export interface DurationTrendData {
  labels: string[];
  durations: number[];
  mean: number;
  stdDevPlus: number;
  stdDevMinus: number;
}

export function computeDurationTrends(entries: TaskHistoryEntry[]): DurationTrendData {
  const sorted = [...entries]
    .filter((e) => (e.task_instance_start_date || e.start_time) && e.duration_seconds != null)
    .sort(
      (a, b) =>
        new Date(a.task_instance_start_date || a.start_time).getTime() -
        new Date(b.task_instance_start_date || b.start_time).getTime(),
    );

  const labels = sorted.map((e) => {
    const d = new Date(e.task_instance_start_date || e.start_time);
    return `${d.toISOString().split('T')[0]} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
  });
  const durations = sorted.map((e) => e.duration_seconds);
  const avg = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
  const sd = stdDev(durations);

  return {
    labels,
    durations,
    mean: avg,
    stdDevPlus: avg + sd,
    stdDevMinus: Math.max(0, avg - sd),
  };
}

// ── Error Analysis ───────────────────────────────────────────────────────────

export interface ErrorFrequencyItem {
  message: string;
  count: number;
}

export interface ErrorListItem {
  logicalDate: string;
  startTime: string;
  errorMessage: string;
  sessionId: string;
  retryNumber: number;
}

export function computeErrorFrequency(
  entries: TaskHistoryEntry[],
  topN = 10,
): ErrorFrequencyItem[] {
  const errors = entries.filter((e) => isError(e.status));
  const countMap = new Map<string, number>();
  for (const e of errors) {
    const msg = extractErrorMessage(e) || 'Unknown error';
    const truncated = msg.length > 120 ? msg.substring(0, 120) + '...' : msg;
    countMap.set(truncated, (countMap.get(truncated) || 0) + 1);
  }
  return [...countMap.entries()]
    .map(([message, count]) => ({ message, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, topN);
}

export function computeErrorList(entries: TaskHistoryEntry[]): ErrorListItem[] {
  return entries
    .filter((e) => isError(e.status))
    .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
    .map((e) => ({
      logicalDate: e.logical_date || 'N/A',
      startTime: e.task_instance_start_date || e.start_time,
      errorMessage: extractErrorMessage(e),
      sessionId: e.session_id,
      retryNumber: e.retry_number,
    }));
}

// ── Retry Breakdown ──────────────────────────────────────────────────────────

export interface RetryDepthItem {
  label: string;
  count: number;
}

export interface RetryOutcomeData {
  labels: string[];
  succeeded: number[];
  failed: number[];
}

export function computeRetryDepthDistribution(entries: TaskHistoryEntry[]): RetryDepthItem[] {
  const countMap = new Map<number, number>();
  for (const e of entries) {
    const depth = e.retry_number ?? 0;
    const key = depth >= 3 ? 3 : depth;
    countMap.set(key, (countMap.get(key) || 0) + 1);
  }
  return [0, 1, 2, 3]
    .filter((k) => countMap.has(k))
    .map((k) => ({
      label: k === 3 ? '3+' : String(k),
      count: countMap.get(k) || 0,
    }));
}

export function computeRetryOutcome(entries: TaskHistoryEntry[]): RetryOutcomeData {
  const retried = entries.filter((e) => (e.retry_number ?? 0) > 0);
  const byDepth = new Map<string, { succeeded: number; failed: number }>();

  for (const e of retried) {
    const depth = e.retry_number >= 3 ? '3+' : String(e.retry_number);
    if (!byDepth.has(depth)) byDepth.set(depth, { succeeded: 0, failed: 0 });
    const b = byDepth.get(depth)!;
    if (e.status === 'success') b.succeeded++;
    else b.failed++;
  }

  const sorted = [...byDepth.entries()].sort(([a], [b]) => a.localeCompare(b));
  return {
    labels: sorted.map(([k]) => `Retry ${k}`),
    succeeded: sorted.map(([, v]) => v.succeeded),
    failed: sorted.map(([, v]) => v.failed),
  };
}

// ── Execution Lag ────────────────────────────────────────────────────────────

export interface ExecutionLagData {
  labels: string[];
  lagSeconds: number[];
}

export function computeExecutionLag(entries: TaskHistoryEntry[]): ExecutionLagData {
  const sorted = [...entries]
    .filter((e) => e.frequency !== 'ADHOC' && e.task_instance_start_date && e.next_run_date)
    .sort(
      (a, b) =>
        new Date(a.task_instance_start_date!).getTime() -
        new Date(b.task_instance_start_date!).getTime(),
    );

  const labels: string[] = [];
  const lagSeconds: number[] = [];

  // lag[i] = task_instance_start_date[i] - next_run_date[i-1]
  for (let i = 1; i < sorted.length; i++) {
    const instanceStart = new Date(sorted[i].task_instance_start_date!).getTime();
    const scheduled = new Date(sorted[i - 1].next_run_date!).getTime();
    if (isNaN(instanceStart) || isNaN(scheduled)) continue;
    const d = new Date(sorted[i].task_instance_start_date!);
    labels.push(
      `${d.toISOString().split('T')[0]} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`,
    );
    lagSeconds.push((instanceStart - scheduled) / 1000);
  }

  return { labels, lagSeconds };
}

export interface HistogramData {
  labels: string[];
  counts: number[];
}

export function computeLagHistogram(entries: TaskHistoryEntry[], bucketCount = 10): HistogramData {
  const { lagSeconds } = computeExecutionLag(entries);
  return buildHistogram(lagSeconds, bucketCount, 's');
}

// ── Duration Histogram ───────────────────────────────────────────────────────

export function computeDurationHistogram(
  entries: TaskHistoryEntry[],
  bucketCount = 10,
): HistogramData {
  const durations = entries.map((e) => e.duration_seconds).filter((d) => d != null && !isNaN(d));
  return buildHistogram(durations, bucketCount, 's');
}

function buildHistogram(values: number[], bucketCount: number, unit: string): HistogramData {
  if (values.length === 0) return { labels: [], counts: [] };

  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return { labels: [`${min.toFixed(1)}${unit}`], counts: [values.length] };
  }

  const range = max - min;
  const bucketSize = range / bucketCount;
  const counts = new Array(bucketCount).fill(0);

  for (const v of values) {
    let idx = Math.floor((v - min) / bucketSize);
    if (idx >= bucketCount) idx = bucketCount - 1;
    counts[idx]++;
  }

  const labels = counts.map((_, i) => {
    const lo = min + i * bucketSize;
    const hi = lo + bucketSize;
    return `${lo.toFixed(2)}-${hi.toFixed(2)}${unit}`;
  });

  return { labels, counts };
}

// ── Consecutive Failure Streaks ──────────────────────────────────────────────

export interface StreakData {
  startTime: string;
  endTime: string;
  length: number;
}

export function computeConsecutiveFailureStreaks(entries: TaskHistoryEntry[]): StreakData[] {
  const sorted = [...entries].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
  );

  const streaks: StreakData[] = [];
  let current: TaskHistoryEntry[] = [];

  for (const e of sorted) {
    if (isError(e.status)) {
      current.push(e);
    } else {
      if (current.length >= 2) {
        streaks.push({
          startTime: current[0].start_time,
          endTime: current[current.length - 1].start_time,
          length: current.length,
        });
      }
      current = [];
    }
  }
  if (current.length >= 2) {
    streaks.push({
      startTime: current[0].start_time,
      endTime: current[current.length - 1].start_time,
      length: current.length,
    });
  }

  return streaks.sort((a, b) => b.length - a.length);
}

export function computeMaxSuccessStreak(entries: TaskHistoryEntry[]): number {
  const sorted = [...entries].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime(),
  );
  let max = 0;
  let current = 0;
  for (const e of sorted) {
    if (e.status === 'success') {
      current++;
      if (current > max) max = current;
    } else {
      current = 0;
    }
  }
  return max;
}

// ── Granularity helper ───────────────────────────────────────────────────────

export function autoGranularity(dateFrom: string, dateTo: string): TimeGranularity {
  const from = new Date(dateFrom).getTime();
  const to = new Date(dateTo).getTime();
  const hours = (to - from) / (1000 * 60 * 60);
  if (hours <= 24) return 'hour';
  if (hours <= 168) return 'day'; // up to 1 week
  return 'week';
}
