/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import {
  datesInRange,
  fetchFileContent,
  fetchListItems,
  parseRunFile,
  today,
} from './useTaskHistory';
import type { TaskHistoryEntry } from './useTaskHistory';

// How far back to look for recent runs. Bounds the number of partition list
// calls per task row.
const RECENT_RUNS_LOOKBACK_DAYS = 14;

export interface UseRecentRunsResult {
  runs: TaskHistoryEntry[];
  loading: boolean;
}

/**
 * Lightweight, bounded variant of {@link useTaskHistory} for showing a small
 * strip of a task's most recent runs in a dense list (e.g. a table row).
 *
 * Lists the last {@link RECENT_RUNS_LOOKBACK_DAYS} day-partitions in parallel,
 * then reads only the newest `limit` files (ranked by file mtime) — so the
 * expensive file reads stay capped at `limit` per task regardless of how
 * frequently the task runs. Pass `enabled=false` to defer fetching until the
 * row is on screen.
 *
 * Returned runs are ordered oldest → newest (newest renders on the right).
 *
 * `refreshKey` is an opaque value; changing it forces a re-fetch (e.g. when the
 * surrounding table is refreshed).
 */
export function useRecentRuns(
  taskLaui: string,
  limit = 15,
  enabled = true,
  refreshKey = 0,
): UseRecentRunsResult {
  const [runs, setRuns] = useState<TaskHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!enabled || !taskLaui) return;
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      try {
        const to = today();
        const from = (() => {
          const d = new Date(to);
          d.setDate(d.getDate() - (RECENT_RUNS_LOOKBACK_DAYS - 1));
          return d.toISOString().split('T')[0];
        })();
        const dates = datesInRange(from, to);

        // List every day-partition in parallel and collect history file refs
        // (without reading their contents yet).
        type FileRef = { folderPath: string; name: string; modified: number; date: string };
        const refs: FileRef[] = [];
        await Promise.all(
          dates.map(async (date) => {
            try {
              const [y, m, d] = date.split('-');
              const folderPath = `category=TASK_HISTORY/task_laui=${taskLaui}/yyyy=${y}/mm=${m}/dd=${d}`;
              const items = await fetchListItems(folderPath);
              for (const item of items) {
                if (
                  item.type === 'file' &&
                  typeof item.name === 'string' &&
                  item.name.endsWith('.log') &&
                  !item.name.startsWith('latest_')
                ) {
                  refs.push({
                    folderPath,
                    name: item.name,
                    modified: typeof item.modified === 'number' ? item.modified : 0,
                    date,
                  });
                }
              }
            } catch {
              /* skip date */
            }
          }),
        );

        // Read only the newest `limit` files (bounded cost regardless of how
        // often the task runs).
        refs.sort((a, b) => b.modified - a.modified);
        const newest = refs.slice(0, limit);

        const parsed = await Promise.all(
          newest.map(async (ref) => {
            try {
              const content = await fetchFileContent(`${ref.folderPath}/${ref.name}`);
              return parseRunFile(content, ref.name, ref.date);
            } catch {
              return null;
            }
          }),
        );

        const entries = parsed.filter((e): e is TaskHistoryEntry => e != null);
        // Display oldest → newest so the newest run sits on the right.
        entries.sort((a, b) => {
          const ta = new Date(a.start_time).getTime() || 0;
          const tb = new Date(b.start_time).getTime() || 0;
          return ta - tb;
        });

        if (!cancelled) setRuns(entries);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, [taskLaui, limit, enabled, refreshKey]);

  return { runs, loading };
}
