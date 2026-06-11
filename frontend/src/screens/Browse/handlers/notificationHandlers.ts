/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
export interface Notification {
  message: string;
  detail?: any;
  sessionId?: string;
}

export interface NotificationPayload {
  type: 'success' | 'error';
  notification: Notification;
}

export const notify = {
  success: (notification: Notification): void => {
    window.dispatchEvent(
      new CustomEvent<NotificationPayload>('SHOW_NOTIFICATION', {
        detail: { type: 'success', notification },
      }),
    );
  },
  error: (notification: Notification): void => {
    window.dispatchEvent(
      new CustomEvent<NotificationPayload>('SHOW_NOTIFICATION', {
        detail: { type: 'error', notification },
      }),
    );
  },
};
