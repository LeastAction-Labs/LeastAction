/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { notify } from '@/screens/Browse/handlers/notificationHandlers';

import { MARKETPLACE_URL } from '../config/urls';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export type JsonRecord = Record<string, unknown>;

export type ApiError = {
  status: number;
  message: string;
  details?: unknown;
};

// Session ID tracking
const sessionIdSet = new Set<string>();
let lastSessionId: string | null = null;

// Callback for when new session IDs are added
let sessionIdCallback: ((sessionIds: Set<string>) => void) | null = null;

// Callback for when a 401 Unauthorized is received
let unauthorizedCallback: (() => void) | null = null;

export function setUnauthorizedCallback(cb: () => void) {
  unauthorizedCallback = cb;
}

export function setSessionIdCallback(callback: (sessionIds: Set<string>) => void) {
  sessionIdCallback = callback;
}

export function getSessionIds(): Set<string> {
  return new Set(sessionIdSet);
}

export function getLastSessionId(): string | null {
  return lastSessionId;
}

function addSessionId(sessionId: string) {
  if (sessionId && typeof sessionId === 'string') {
    sessionIdSet.add(sessionId);
    lastSessionId = sessionId;
    if (sessionIdCallback) {
      sessionIdCallback(new Set(sessionIdSet));
    }
  }
}

function safeStringify(value: unknown): string {
  try {
    if (typeof value === 'string') return value;
    const str = JSON.stringify(value, null, 2);
    return str ?? '';
  } catch {
    return '[unserializable]';
  }
}

function logBox(_title: string, _content: string, _isError = false) {
  // const color = isError ? "\x1b[31m" : "\x1b[36m"; // Red for errors, Cyan for success
  // const reset = "\x1b[0m";
  // const bold = "\x1b[1m";
  // const border = "═".repeat(60);
  //console.log(`\n${color}${bold}╔${border}╗${reset}`);
  //console.log(`${color}${bold}║ ${title.padEnd(59)}║${reset}`);
  //console.log(`${color}${bold}╠${border}╣${reset}`);
  // const lines = content.split("\n");
  // lines.forEach(line => {
  //console.log(`${color}║${reset} ${line}`);
  // });
  //console.log(`${color}${bold}╚${border}╝${reset}\n`);
}

const nonEmptyString = (v: unknown): v is string => typeof v === 'string' && v.trim() !== '';

// Derive a human-readable message from an error response body. Backend errors
// come in several shapes and don't reliably carry a top-level `message`:
//   - Middleware errors:  { message, detail }
//   - Route HTTPException: { detail: { message, detail } }   (FastAPI nests it)
//   - Plain FastAPI:       { detail: "..." }
//   - Validation errors:   { detail: [ ... ] }
//   - Non-JSON / empty body parses to null
// Without unwrapping the nested case the banner renders empty even though the
// real error is visible in the network response.
function extractErrorMessage(data: any, res: Response): string {
  if (data && typeof data === 'object') {
    if (nonEmptyString(data.message)) return data.message;

    const detail = data.detail;
    if (nonEmptyString(detail)) return detail;
    // FastAPI HTTPException wraps our { message, detail } under `detail`.
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      if (nonEmptyString(detail.message)) return detail.message;
      if (nonEmptyString(detail.detail)) return detail.detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as Record<string, unknown>;
      if (first && nonEmptyString(first.msg)) return first.msg;
      return 'Validation error';
    }
  }
  if (nonEmptyString(data)) return data;
  return `Request failed (${res.status} ${res.statusText || 'Error'})`;
}

function parseJsonSafe<T>(text: string): T | null {
  try {
    if (!text || text.trim() === '') {
      return null;
    }
    return JSON.parse(text) as T;
  } catch (error) {
    console.error('Error parsing JSON response:', error, 'Text:', text);
    return null;
  }
}

export async function httpJson<TResponse>(
  input: string,
  init?: Omit<RequestInit, 'body'> & { method?: HttpMethod; body?: JsonRecord },
): Promise<TResponse> {
  const method = init?.method || 'GET';

  // Log request
  const requestInfo = {
    method,
    url: input,
    headers: init?.headers,
    body: init?.body,
  };

  logBox(`🚀 API REQUEST - ${method} ${input}`, safeStringify(requestInfo));

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init?.headers ?? {}),
  };

  const body = init?.body ? JSON.stringify(init.body) : undefined;

  const res = await fetch(input, { ...init, headers, body, credentials: 'include' });

  // Read response text once (can only be read once)
  const responseText = await res.text();
  const data: any = parseJsonSafe<TResponse>(responseText);

  // Extract and track session_id from X-Session-ID header
  const sessionId = res.headers.get('X-Session-ID');
  if (sessionId && typeof sessionId === 'string' && sessionId.trim() !== '') {
    addSessionId(sessionId);
  }

  if (!res.ok) {
    if (res.status === 401 && unauthorizedCallback && !input.startsWith(MARKETPLACE_URL)) {
      unauthorizedCallback();
    }
    const message = extractErrorMessage(data, res);
    const errData =
      data && typeof data === 'object' ? (data as Record<string, unknown>) : undefined;
    if (!input.includes('check')) {
      notify.error({ ...errData, message, sessionId: sessionId ?? undefined });
    }
    throw new Error(message);
  }

  const successInfo = {
    status: res.status,
    statusText: res.statusText,
    url: input,
    data,
    contentType: res.headers.get('content-type'),
  };

  logBox(`✅ API SUCCESS - ${res.status} ${res.statusText}`, safeStringify(successInfo));

  // If server legitimately returns no body or null, return empty object
  // But log a warning if we expected data
  if (data === null) {
    console.warn(`API returned null/empty response for ${input}. Status: ${res.status}`);
  }

  return (data as TResponse) ?? ({} as TResponse);
}

export interface HttpJsonWithSessionResponse<T> {
  data: T;
  sessionId: string | null;
}

export async function httpJsonWithSession<TResponse>(
  input: string,
  init?: Omit<RequestInit, 'body' | 'method'> & {
    method?: HttpMethod;
    body?: JsonRecord;
  },
): Promise<HttpJsonWithSessionResponse<TResponse>> {
  const method = init?.method || 'GET';

  const requestInfo = {
    method,
    url: input,
    headers: init?.headers,
    body: init?.body,
  };

  logBox(`API REQUEST - ${method} ${input}`, safeStringify(requestInfo));

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init?.headers ?? {}),
  };

  const body = init?.body ? JSON.stringify(init.body) : undefined;

  const res = await fetch(input, { ...init, headers, body, credentials: 'include' });

  const responseText = await res.text();
  const data: any = parseJsonSafe<TResponse>(responseText);

  const sessionId = res.headers.get('X-Session-ID');
  if (sessionId && typeof sessionId === 'string' && sessionId.trim() !== '') {
    addSessionId(sessionId);
  }

  if (!res.ok) {
    if (res.status === 401 && unauthorizedCallback && !input.startsWith(MARKETPLACE_URL)) {
      unauthorizedCallback();
    }
    const message = extractErrorMessage(data, res);
    const errData =
      data && typeof data === 'object' ? (data as Record<string, unknown>) : undefined;
    notify.error({ ...errData, message, sessionId: sessionId ?? undefined });
    throw new Error(message);
  }

  const successInfo = {
    status: res.status,
    statusText: res.statusText,
    url: input,
    data,
    sessionId,
  };

  logBox(`API SUCCESS - ${res.status} ${res.statusText}`, safeStringify(successInfo));

  return {
    data: (data as TResponse) ?? ({} as TResponse),
    sessionId: sessionId || null,
  };
}
