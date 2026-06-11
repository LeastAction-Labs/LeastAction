/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Log-related constants for colors, levels, and parsing.
 * Centralized here so they can be changed in one place.
 */
import { COLORS } from './index';

// ── Log Level Colors ────────────────────────────────────────────────────────
// Used for coloring log lines in the stream viewer.
export const LOG_LEVEL_COLORS: Record<string, { text: string; bg: string }> = {
  INFO: { text: COLORS.GREEN, bg: 'transparent' },
  ERROR: { text: COLORS.RED, bg: COLORS.RED_BG_SOFT },
  WARNING: { text: COLORS.AMBER, bg: 'transparent' },
  DEBUG: { text: COLORS.PURPLE, bg: 'transparent' },
  CRITICAL: { text: COLORS.RED, bg: COLORS.RED_BG },
};

// ── Execution Status Colors ─────────────────────────────────────────────────
// Used for status badges, timeline dots, and sidebar session blocks.
export const STATUS_COLORS: Record<
  string,
  { dot: string; badge: string; badgeBg: string; text: string }
> = {
  success: {
    dot: COLORS.GREEN,
    badge: COLORS.GREEN,
    badgeBg: COLORS.GREEN_BG,
    text: COLORS.GREEN,
  },
  failed: { dot: COLORS.RED, badge: COLORS.RED, badgeBg: COLORS.RED_BG, text: COLORS.RED },
  error: { dot: COLORS.RED, badge: COLORS.RED, badgeBg: COLORS.RED_BG, text: COLORS.RED },
  running: {
    dot: COLORS.AMBER,
    badge: COLORS.AMBER,
    badgeBg: COLORS.AMBER_BG,
    text: COLORS.AMBER,
  },
  pending: { dot: COLORS.BLUE, badge: COLORS.BLUE, badgeBg: COLORS.BLUE_BG, text: COLORS.BLUE },
  queued: { dot: COLORS.BLUE, badge: COLORS.BLUE, badgeBg: COLORS.BLUE_BG, text: COLORS.BLUE },
};

// ── Filter Options ──────────────────────────────────────────────────────────
export const LOG_LEVELS = ['ALL', 'INFO', 'ERROR', 'WARNING', 'DEBUG', 'CRITICAL'] as const;
export type LogLevel = (typeof LOG_LEVELS)[number];

// ── Parsing ─────────────────────────────────────────────────────────────────
// JSON log format (one JSON object per line):
//   {"timestamp":"2026-02-19T04:19:53.123456","level":"info","step":"step_name","session_id":"...","message":"..."}

export interface ParsedLogLine {
  date: string;
  time: string;
  level: string;
  tag: string; // step_name
  message: string;
}

/**
 * Parse a JSON-per-line log entry into structured fields.
 * Returns raw line as `message` if the line is not valid JSON.
 */
export function parseLogLine(line: string): ParsedLogLine {
  const trimmed = line.trim();

  if (trimmed.startsWith('{')) {
    try {
      const obj = JSON.parse(trimmed);
      if (obj.timestamp && obj.level && obj.message !== undefined) {
        const ts = obj.timestamp as string;
        const sep = ts.includes('T') ? 'T' : ' ';
        const [datePart = '', timePart = ''] = ts.split(sep);
        return {
          date: datePart,
          time: timePart.substring(0, 8),
          level: (obj.level as string).toUpperCase(),
          tag: (obj.step as string) ?? '',
          message: obj.message as string,
        };
      }
    } catch {
      /* fall through */
    }
  }

  return { date: '', time: '', level: '', tag: '', message: line };
}

// ── Category display names ──────────────────────────────────────────────────
export const CATEGORY_LABELS: Record<string, string> = {
  TASK: 'Tasks',
  PRE_ACTION: 'Pre-action',
  POST_ACTION: 'Post-action',
  RUNNING_ACTION: 'Running Action',
  CELERY: 'Celery',
  API: 'API',
  ACTION: 'Action',
};
