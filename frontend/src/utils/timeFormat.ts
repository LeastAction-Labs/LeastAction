/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Centralized time formatting utility.
 * Reads timezone preference from localStorage.
 *
 * Backend stores all datetimes in UTC. Timestamps may arrive with or
 * without a trailing "Z" (MongoDB can return naive datetimes). We
 * normalise every incoming string so `new Date()` always parses it
 * as UTC — never as browser-local time.
 */

export type TimeZoneMode = 'utc' | 'local';

export function getTimeZoneMode(): TimeZoneMode {
  const saved = localStorage.getItem('app-timezone');
  return saved === 'local' ? 'local' : 'utc';
}

function isUTC(): boolean {
  return getTimeZoneMode() === 'utc';
}

/**
 * Ensure the string is parsed as UTC.
 * If it already ends with "Z" or carries a +/- offset, leave it alone.
 * Otherwise append "Z" so the browser doesn't treat it as local time.
 */
function ensureUTC(s: string): string {
  const t = s.trim();
  if (/Z$/i.test(t) || /[+-]\d{2}:?\d{2}$/.test(t)) return t;
  return t.replace(' ', 'T') + 'Z';
}

/** Parse a date string, always treating ambiguous timestamps as UTC */
function parse(s: string): Date {
  return new Date(ensureUTC(s));
}

// ── Formatting helpers ──────────────────────────────────────────────

/** Full date+time: "5/28/2026, 2:30:00 PM" */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const d = parse(dateString);
    if (isNaN(d.getTime())) return String(dateString);
    if (isUTC()) return d.toLocaleString('en-US', { timeZone: 'UTC' });
    return d.toLocaleString();
  } catch {
    return String(dateString);
  }
}

/** Compact: "5/28/26, 2:30 PM" */
export function formatDateTimeCompact(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const d = parse(dateString);
    if (isNaN(d.getTime())) return String(dateString);
    const opts: Intl.DateTimeFormatOptions = {
      month: 'numeric',
      day: 'numeric',
      year: '2-digit',
      hour: 'numeric',
      minute: '2-digit',
    };
    if (isUTC()) opts.timeZone = 'UTC';
    return d.toLocaleString('en-US', opts);
  } catch {
    return String(dateString);
  }
}

/** YYYY-MM-DD HH:MM:SS */
export function formatDateTimeFull(isoStr: string): string {
  if (!isoStr) return 'N/A';
  try {
    const d = parse(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    if (isUTC()) {
      const date = d.toISOString().split('T')[0];
      const time = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}:${String(d.getUTCSeconds()).padStart(2, '0')}`;
      return `${date} ${time}`;
    }
    const date = d.toLocaleDateString('en-CA');
    const time = d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    return `${date} ${time}`;
  } catch {
    return isoStr;
  }
}

/** YYYY-MM-DD HH:MM (no seconds) */
export function formatDateTimeShort(isoStr: string): string {
  if (!isoStr) return '';
  try {
    const d = parse(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    if (isUTC()) {
      return `${d.toISOString().split('T')[0]} ${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
    }
    const date = d.toLocaleDateString('en-CA');
    const time = d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    });
    return `${date} ${time}`;
  } catch {
    return isoStr;
  }
}

/** Date only: "May 28, 2026" — pure-date strings are not shifted */
export function formatDateOnly(dateStr: string): string {
  if (!dateStr) return 'N/A';
  try {
    const plain = dateStr.split(/[T ]/)[0];
    const [y, m, d] = plain.split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/** Inline: "Jan 5, 2:30 PM" */
export function formatDateTimeInline(dateString: string | null | undefined): string {
  if (!dateString) return 'N/A';
  try {
    const d = parse(String(dateString));
    if (isNaN(d.getTime())) return String(dateString);
    const opts: Intl.DateTimeFormatOptions = {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    };
    if (isUTC()) opts.timeZone = 'UTC';
    return d.toLocaleString(undefined, opts);
  } catch {
    return String(dateString);
  }
}

/** { date, time } pair — used by SchedulerTab */
export function formatTimestampParts(timestamp: string): { date: string; time: string } {
  const d = parse(timestamp);
  if (isUTC()) {
    return {
      date: d.toISOString().split('T')[0],
      time: `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}:${String(d.getUTCSeconds()).padStart(2, '0')}`,
    };
  }
  return {
    date: d.toLocaleDateString('en-CA'),
    time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`,
  };
}

/** For table columns — strip microseconds or convert to local */
export function formatDateValue(value: string): string {
  if (isUTC()) {
    return value
      .replace('T', ' ')
      .replace(/\.\d+$/, '')
      .replace(/Z$/, '');
  }
  try {
    const d = parse(value);
    if (isNaN(d.getTime()))
      return value
        .replace('T', ' ')
        .replace(/\.\d+$/, '')
        .replace(/Z$/, '');
    const date = d.toLocaleDateString('en-CA');
    const time = d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    return `${date} ${time}`;
  } catch {
    return value
      .replace('T', ' ')
      .replace(/\.\d+$/, '')
      .replace(/Z$/, '');
  }
}

/** Time of day only: "2:30 PM" */
export function formatTimeOnly(date: Date): string {
  if (isUTC()) {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Date only via toLocaleDateString */
export function formatLocalDate(dateString: string): string {
  if (!dateString) return 'N/A';
  try {
    const d = parse(dateString);
    if (isNaN(d.getTime())) return dateString;
    if (isUTC()) return d.toLocaleDateString('en-US', { timeZone: 'UTC' });
    return d.toLocaleDateString();
  } catch {
    return dateString;
  }
}

/** Timezone label for the toggle button */
export function getTimeZoneLabel(): string {
  if (isUTC()) return 'UTC';
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'Local';
  }
}
