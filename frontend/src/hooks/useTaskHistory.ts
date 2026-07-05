/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useState } from 'react';

import { buildLogApiUrl, consumeSSE } from '@/services/sseHelper';

// ── Types ────────────────────────────────────────────────────────────────────

export interface TaskHistoryEntry {
  task_laui: string;
  task_name: string;
  operator_laui: string;
  session_id: string;
  partition: string;

  state: string;
  status: string;
  user_set_state: string | null;

  start_time: string;
  duration_seconds: number;
  logical_date: string;
  data_interval_start: string | null;
  data_interval_end: string | null;
  prev_interval_start: string | null;
  prev_interval_end: string | null;
  task_instance_start_date: string | null;
  task_instance_end_date: string | null;
  last_run_date: string | null;
  next_run_date: string | null;

  frequency: string;
  iteration: number;
  retry_number: number;
  total_retries: number;
  retry_interval: number;
  can_retry: boolean;
  task_reschedule_count: number;

  executor: string | null;
  task_instance: string | null;
  priority: number;

  actions_status: {
    pre_actions: any[];
    running_actions: any[];
    post_actions: any[];
  };

  output: any;

  fileName: string;
  /** YYYY-MM-DD partition date this entry was fetched from */
  _date: string;
}

export interface LatestFile {
  name: string;
  logUrl: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function parseDate(s: string) {
  return s.split(/[T ]/)[0];
}

export function today() {
  return new Date().toISOString().split('T')[0];
}

export function datesInRange(from: string, to: string): string[] {
  const dates: string[] = [];
  const cur = new Date(from);
  const end = new Date(to);
  while (cur <= end) {
    dates.push(cur.toISOString().split('T')[0]);
    cur.setDate(cur.getDate() + 1);
  }
  return dates;
}

export function fetchListItems(folderPath: string): Promise<any[]> {
  return new Promise((resolve, reject) => {
    const items: any[] = [];
    consumeSSE(buildLogApiUrl(`listItems/${folderPath}`), {
      onEvent(type, data: any) {
        if (type === 'data' && data?.items) items.push(...data.items);
        else if (type === 'error') reject(new Error(data?.message ?? 'List failed'));
      },
      onError: reject,
      onDone: () => resolve(items),
    });
  });
}

export function fetchFileContent(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    let content = '';
    consumeSSE(buildLogApiUrl(`file/${filePath}`), {
      onEvent(type, data: any) {
        if (type === 'chunk' && data?.content) content += data.content;
        else if (type === 'error') reject(new Error(data?.message ?? 'File read failed'));
      },
      onError: reject,
      onDone: () => resolve(content),
    });
  });
}

/**
 * Parse a single TASK_HISTORY `.log` file into a TaskHistoryEntry.
 *
 * The file is a sequence of JSON log lines that we merge into one record. The
 * history log's `state` field is the task state at log time (often
 * "queued_in_redis" or "running"), NOT the final outcome — so we derive a
 * final execution `status` from the available signals when one isn't present.
 *
 * Returns `null` when the file contains no usable JSON.
 */
export function parseRunFile(
  content: string,
  fileName: string,
  date: string,
): TaskHistoryEntry | null {
  const merged: Record<string, any> = {};
  for (const rawLine of content.split('\n')) {
    const trimmed = rawLine.trim();
    if (!trimmed.startsWith('{')) continue;
    try {
      const outer = JSON.parse(trimmed);
      Object.assign(merged, outer);
      if (typeof outer.message === 'string' && outer.message.trim().startsWith('{')) {
        try {
          const inner = JSON.parse(outer.message);
          Object.assign(merged, inner);
        } catch {
          /* message is plain text */
        }
      }
    } catch {
      /* skip malformed lines */
    }
  }
  if (Object.keys(merged).length === 0) return null;

  // If output is a string, try to parse it as JSON
  if (typeof merged.output === 'string') {
    try {
      merged.output = JSON.parse(merged.output);
    } catch {
      /* keep as-is */
    }
  }

  // Derive final execution status from available signals.
  if (!merged.status) {
    const outputErr = merged.output?.error || merged.error;
    const outputMsg = merged.output?.message;
    if (outputErr) {
      merged.status = 'error';
    } else if (merged.user_set_state === 'cancel') {
      merged.status = 'cancelled';
    } else if (
      ['success', 'error', 'failed', 'fail', 'timeout', 'cancelled'].includes(merged.state)
    ) {
      merged.status = merged.state;
    } else if (typeof outputMsg === 'string' && /timed?\s*out/i.test(outputMsg)) {
      merged.status = 'timeout';
    } else if (merged.output?.run_output && !outputErr) {
      merged.status = 'success';
    } else if (merged.duration_seconds != null && merged.duration_seconds > 0 && !outputErr) {
      // Completed with duration and no error — likely success
      merged.status = 'success';
    } else {
      merged.status = merged.state || 'unknown';
    }
  }

  return {
    ...merged,
    fileName,
    _date: date,
  } as TaskHistoryEntry;
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UseTaskHistoryResult {
  entries: TaskHistoryEntry[];
  latestFiles: LatestFile[];
  loading: boolean;
  refetch: () => void;
}

export function useTaskHistory(
  taskLaui: string,
  dateFrom: string,
  dateTo: string,
): UseTaskHistoryResult {
  const [entries, setEntries] = useState<TaskHistoryEntry[]>([]);
  const [latestFiles, setLatestFiles] = useState<LatestFile[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!taskLaui || !dateFrom || !dateTo) return;
    setLoading(true);
    setEntries([]);
    setLatestFiles([]);

    const dates = datesInRange(dateFrom, dateTo);
    const entriesByDate: { date: string; entries: TaskHistoryEntry[] }[] = [];
    const latestByName = new Map<string, LatestFile>();

    await Promise.all(
      dates.map(async (date) => {
        try {
          const [y, m, d] = date.split('-');
          const folderPath = `category=TASK_HISTORY/task_laui=${taskLaui}/yyyy=${y}/mm=${m}/dd=${d}`;
          const items = await fetchListItems(folderPath);

          for (const item of items) {
            if (
              item.type === 'file' &&
              item.name.startsWith('latest_') &&
              item.name.endsWith('.log') &&
              !latestByName.has(item.name)
            ) {
              latestByName.set(item.name, {
                name: item.name,
                logUrl: `file/${folderPath}/${item.name}`,
              });
            }
          }

          const historyFiles = items.filter(
            (item: any) =>
              item.type === 'file' &&
              item.name.endsWith('.log') &&
              !item.name.startsWith('latest_'),
          );

          const dateEntries: TaskHistoryEntry[] = [];
          await Promise.all(
            historyFiles.map(async (file: any) => {
              try {
                const content = await fetchFileContent(`${folderPath}/${file.name}`);
                const entry = parseRunFile(content, file.name, date);
                if (entry) dateEntries.push(entry);
              } catch {
                /* skip */
              }
            }),
          );

          if (dateEntries.length > 0) {
            entriesByDate.push({ date, entries: dateEntries });
          }
        } catch {
          /* skip date */
        }
      }),
    );

    entriesByDate.sort((a, b) => b.date.localeCompare(a.date));
    setLatestFiles([...latestByName.values()]);

    const flat: TaskHistoryEntry[] = [];
    for (const { entries } of entriesByDate) {
      entries.sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime());
      flat.push(...entries);
    }
    setEntries(flat);
    setLoading(false);
  }, [taskLaui, dateFrom, dateTo]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  return { entries, latestFiles, loading, refetch: () => void fetchData() };
}
