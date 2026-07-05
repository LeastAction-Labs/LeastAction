/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// services/task.service.ts
import { CORE_BACKEND_URL } from '@/config/urls';

import { getCatalogItemById } from '.';
import { httpJsonWithSession } from './api';
import { preprocessItemData } from './utils';

const API_ENDPOINTS = {
  task: {
    run: `${CORE_BACKEND_URL}/api/v1/task/run`,
    run_multiple: `${CORE_BACKEND_URL}/api/v1/task/multiple_tasks`,
    dangerously_reset: `${CORE_BACKEND_URL}/api/v1/task/dangerously_reset`,
    diagnose: `${CORE_BACKEND_URL}/api/v1/task/diagnose`,
  },
};

export interface TaskRunRequest extends Record<string, unknown> {
  item_type: string;
}

export interface TaskRunResponse {
  item_laui?: string;
  session_id?: string;
  [key: string]: any;
}

/**
 * Execute/Run a task
 * @param taskData - Task data including item_type and other task fields
 * @returns Promise with task run response
 */
export async function runTask(taskData: any): Promise<TaskRunResponse> {
  //console.log('Running task with data:', taskData);
  try {
    const cleanedItemData = await preprocessItemData(taskData);
    const { data, sessionId } = await httpJsonWithSession<TaskRunResponse>(API_ENDPOINTS.task.run, {
      method: 'POST',
      body: cleanedItemData,
    });
    //console.log('Task run response:', data, 'Session ID:', sessionId);
    return { ...data, session_id: sessionId || data.session_id || undefined };
  } catch (error) {
    console.error('Error running task:', error);
    throw error;
  }
}

/**
 * Run multiple tasks
 * @param taskLauis - Array of task LAUIs to run
 * @returns Promise with array of task run responses
 */
export async function runTasks(taskLauis: string[]): Promise<TaskRunResponse[]> {
  //console.log('Running multiple tasks:', taskLauis);
  try {
    const { data, sessionId } = await httpJsonWithSession<TaskRunResponse>(
      API_ENDPOINTS.task.run_multiple,
      {
        method: 'POST',
        body: { task_lauis: taskLauis },
      },
    );
    return [{ ...data, session_id: sessionId || data.session_id || undefined }];
  } catch (error) {
    console.error('Error running multiple tasks:', error);
    throw error;
  }
}

/**
 * Cancel a task by setting user_set_state = "cancel"
 * Uses the task update endpoint so backend logic can also set state to "cancelled"
 * when the task is not in an active state (queued_for_connection, queued_in_redis, running).
 * @param taskLaui - The LAUI of the task to cancel
 */
export async function cancelTask(taskLaui: string): Promise<void> {
  const task = await getCatalogItemById(taskLaui);
  task.user_set_state = 'cancel';
  await httpJsonWithSession(`${API_ENDPOINTS.task.run}`, {
    method: 'POST',
    body: task,
  });
}

/**
 * Dangerously reset a task - removes from connection queue, resets state to scheduled
 */
export interface DangerouslyResetResponse {
  task_laui: string;
  previous_state: string;
  heartbeat_stale: boolean;
  heartbeat_age_seconds: number | null;
  removed_from_queue: boolean;
}

export async function dangerouslyResetTask(taskLaui: string): Promise<DangerouslyResetResponse> {
  const { data } = await httpJsonWithSession<DangerouslyResetResponse>(
    `${API_ENDPOINTS.task.dangerously_reset}/${taskLaui}`,
    { method: 'POST' },
  );
  return data;
}

/**
 * Diagnose why a task has not run - checks 15 possible failure cases
 */
export interface DiagnosticResult {
  case_id: number;
  title: string;
  passed_title?: string;
  description: string;
  severity: 'blocking' | 'warning' | 'info';
  detected: boolean;
}

export interface TaskDiagnosticResponse {
  task_laui: string;
  task_name: string;
  current_state: string;
  issues_found: number;
  diagnostics: DiagnosticResult[];
}

export async function diagnoseTask(taskLaui: string): Promise<TaskDiagnosticResponse> {
  const { data } = await httpJsonWithSession<TaskDiagnosticResponse>(
    `${API_ENDPOINTS.task.diagnose}/${taskLaui}`,
    { method: 'GET' },
  );
  return data;
}
