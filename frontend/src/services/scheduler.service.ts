/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// services/scheduler.service.ts
import { CORE_BACKEND_URL } from '@/config/urls';
import { formatTimestampParts } from '@/utils/timeFormat';

import { httpJson } from './api';

const API_ENDPOINTS = {
  scheduler: {
    manage: `${CORE_BACKEND_URL}/api/v1/cron/manage`,
  },
};

export interface SchedulerResponse {
  cron_status?: 'RUNNING' | 'STOPPED';
  latest_heartbeat?: string;
  updated_at?: string;
  project_laui?: string;
  error?: string | null;
  message?: string;
}

/**
 * Manage scheduler (start/stop) for a project
 * @param projectLaui - The project LAUI identifier
 * @param action - Action to perform: 'START' or 'STOP'
 * @returns Scheduler response with updated state
 */
export async function manageScheduler(
  projectLaui: string,
  action: 'START' | 'STOP',
): Promise<SchedulerResponse> {
  return await httpJson<SchedulerResponse>(API_ENDPOINTS.scheduler.manage, {
    method: 'POST',
    body: {
      project_laui: projectLaui,
      action: action,
    } as any,
  });
}

/**
 * Calculate delta between two timestamps in seconds
 * @param fromTime - Start timestamp (ISO string or Date)
 * @param toTime - End timestamp (ISO string or Date), defaults to current time
 * @returns Delta in seconds
 */
export function calculateTimeDelta(fromTime: string | Date, toTime?: string | Date): number {
  const from = typeof fromTime === 'string' ? new Date(fromTime) : fromTime;
  const to = typeof toTime === 'string' ? new Date(toTime) : toTime || new Date();

  return Math.floor((to.getTime() - from.getTime()) / 1000);
}

/**
 * Format seconds into human-readable time string
 * @param seconds - Time in seconds
 * @returns Formatted time string (e.g., "06:02:17")
 */
export function formatTimeFromSeconds(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format timestamp to readable date and time
 * @param timestamp - ISO timestamp string
 * @returns Object with formatted date and time
 */
export function formatTimestamp(timestamp: string): { date: string; time: string } {
  return formatTimestampParts(timestamp);
}
