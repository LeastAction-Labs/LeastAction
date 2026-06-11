/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

const API_ENDPOINTS = {
  changePassword: `${CORE_BACKEND_URL}/api/v1/user/change-password`,
  me: `${CORE_BACKEND_URL}/api/v1/user/me`,
  searchUsers: `${CORE_BACKEND_URL}/api/v1/user/search`,
};

export async function getMe(): Promise<{ username: string; email: string }> {
  return await httpJson<{ username: string; email: string }>(API_ENDPOINTS.me, { method: 'GET' });
}

export async function changePassword(
  current_password: string,
  new_password: string,
): Promise<void> {
  await httpJson<{ message: string }>(API_ENDPOINTS.changePassword, {
    method: 'POST',
    body: { current_password, new_password },
  });
}

export async function searchUsers(payload: any) {
  if (!('page' in payload)) payload['page'] = 1;
  if (!('page' in payload)) payload['per_page'] = 10;
  return await httpJson<any>(API_ENDPOINTS.searchUsers, {
    method: 'POST',
    body: payload,
  });
}
