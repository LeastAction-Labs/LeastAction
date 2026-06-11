/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * SSE (Server-Sent Events) helper for consuming streaming responses
 * from the backend logs API.
 *
 * Backend format:
 *   event: <type>\n
 *   data: <json>\n
 *   \n
 */
import { CORE_BACKEND_URL } from '@/config/urls';

export interface SSEHandlers {
  onEvent: (eventType: string, data: unknown) => void;
  onError?: (error: Error) => void;
  onDone?: () => void;
}

/**
 * Consume an SSE stream from `url`. Returns an AbortController the caller can
 * use to cancel the stream.
 */
export function consumeSSE(url: string, handlers: SSEHandlers): AbortController {
  const controller = new AbortController();

  void (async () => {
    try {
      const res = await fetch(url, { signal: controller.signal });
      if (!res.ok) {
        handlers.onError?.(new Error(`HTTP ${res.status}: ${res.statusText}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        handlers.onError?.(new Error('No readable stream'));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages (separated by double newline)
        const parts = buffer.split('\n\n');
        // Keep the last (possibly incomplete) part in the buffer
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          if (!part.trim()) continue;

          let eventType = 'message';
          let dataStr = '';

          for (const line of part.split('\n')) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              dataStr += line.slice(6);
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);
            handlers.onEvent(eventType, data);
          } catch {
            // Non-JSON data, pass as string
            handlers.onEvent(eventType, dataStr);
          }
        }
      }

      handlers.onDone?.();
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // Intentional cancellation – not an error
        return;
      }
      handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}

/**
 * Build a full API URL for the logs endpoints.
 */
export function buildLogApiUrl(path: string): string {
  const apiBaseUrl = CORE_BACKEND_URL || '';
  const base = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
  return `${base}/api/v1/logs/${path}`;
}
