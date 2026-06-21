/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';
import { type PaginationInterface } from './types';

const API_ENDPOINTS = {
  check: `${CORE_BACKEND_URL}/api/v1/admin/check`,
  adminCreate: `${CORE_BACKEND_URL}/api/v1/admin/user/create`,
  adminList: `${CORE_BACKEND_URL}/api/v1/admin/user/list`,
  adminSetStatus: (userId: string) => `${CORE_BACKEND_URL}/api/v1/admin/user/${userId}/status`,
  userDelete: (userId: string) => `${CORE_BACKEND_URL}/api/v1/admin/user/delete/${userId}`,
  userUpdate: (userId: string) => `${CORE_BACKEND_URL}/api/v1/admin/user/update/${userId}`,
  getAllMcpTools: `${CORE_BACKEND_URL}/api/v1/admin/mcp-tools`,
  userMe: `${CORE_BACKEND_URL}/api/v1/user/me`,
  getSystemMarketplaceToken: `${CORE_BACKEND_URL}/api/v1/admin/system_marketplace_access_token/get`,
  updateSystemMarketplaceToken: `${CORE_BACKEND_URL}/api/v1/admin/system_marketplace_access_token/update`,
  uploadLicense: CORE_BACKEND_URL + '/api/v1/admin/license/upload',
  getAllLicenses: CORE_BACKEND_URL + '/api/v1/admin/license/get',
  updateLicense: CORE_BACKEND_URL + '/api/v1/admin/license/update',
};

export async function adminCheck() {
  const data = await httpJson<any>(API_ENDPOINTS.check, { method: 'GET' });
  return data;
}

export interface LicenseUploadRequest {
  publicKey: string;
  licenseId: string;
}

export interface LicenseProjection {
  laui: string;
  license_id: string;
  tier: string;
  status: string;
}

export interface UpdateLicenseRequest {
  laui: string;
  user_list_patch?: {
    add?: string[];
    remove?: string[];
    replace?: string[];
  };
}

export async function uploadLicense(request: LicenseUploadRequest) {
  const body = {
    license_id: request.licenseId,
    public_key: request.publicKey,
  };

  return await httpJson<any>(API_ENDPOINTS.uploadLicense, {
    method: 'POST',
    body: body as unknown as Record<string, unknown>,
  });
}

export async function getLicenses(): Promise<LicenseProjection[]> {
  return await httpJson(API_ENDPOINTS.getAllLicenses, {
    method: 'GET',
  });
}

export async function getLicenseByLaui(laui: string) {
  return await httpJson(API_ENDPOINTS.getAllLicenses + '/' + laui, {
    method: 'GET',
  });
}

export async function updateLicense(request: UpdateLicenseRequest) {
  return await httpJson(API_ENDPOINTS.updateLicense, {
    method: 'POST',
    body: request as unknown as Record<string, unknown>,
  });
}

export interface AdminCreateUserResponse {
  username: string;
  temp_password: string;
}

export interface UserRecord {
  laui: string;
  username: string;
  email: string;
  user_type?: string;
  is_active?: boolean;
  created_at?: string;
  allowed_mcp_tools: string[] | null;
  chat_agent_laui?: string | null;
  chat_connection_laui?: string | null;
  chat_agent_name?: string | null;
}

export async function adminCreateUser(
  username: string,
  email: string,
): Promise<AdminCreateUserResponse> {
  return await httpJson<AdminCreateUserResponse>(API_ENDPOINTS.adminCreate, {
    method: 'POST',
    body: { username, email },
  });
}

export interface ListUsersResponse {
  users: UserRecord[];
  pagination: PaginationInterface;
}

export async function listUsers(page?: number, perPage?: number): Promise<ListUsersResponse> {
  const response = await httpJson<ListUsersResponse>(
    API_ENDPOINTS.adminList + `?page=${page}&per_page=${perPage}`,
    {
      method: 'GET',
    },
  );
  return {
    ...response,
    users: response.users.filter((user) => user.user_type !== 'system'),
  };
}

export async function setUserStatus(userId: string, is_active: boolean): Promise<void> {
  await httpJson<{ message: string }>(API_ENDPOINTS.adminSetStatus(userId), {
    method: 'PATCH',
    body: { is_active },
  });
}

export async function updateUser(userId: string, payload: any): Promise<void> {
  await httpJson<{ message: string }>(API_ENDPOINTS.userUpdate(userId), {
    method: 'POST',
    body: payload,
  });
}

export async function deleteUser(userId: string): Promise<void> {
  await httpJson<{ message: string }>(API_ENDPOINTS.userDelete(userId), {
    method: 'DELETE',
  });
}

export async function getAllMcpTools(): Promise<string[]> {
  const data = await httpJson<{ tools: string[] }>(API_ENDPOINTS.getAllMcpTools, {
    method: 'GET',
  });
  return data.tools;
}

export type McpToolGroups = Record<string, string[]>;

export async function getMcpToolGroups(): Promise<{ tools: string[]; groups: McpToolGroups }> {
  const data = await httpJson<{ tools: string[]; groups?: McpToolGroups }>(
    API_ENDPOINTS.getAllMcpTools,
    { method: 'GET' },
  );
  return { tools: data.tools, groups: data.groups ?? { LeastAction: data.tools } };
}

export async function updateUserMcpTools(
  userId: string,
  allowedTools: string[] | null,
  chatAgentLaui?: string | null,
  chatConnectionLaui?: string | null,
  chatAgentName?: string | null,
): Promise<void> {
  await httpJson(API_ENDPOINTS.userUpdate(userId), {
    method: 'POST',
    body: {
      allowed_mcp_tools: allowedTools,
      ...(chatAgentLaui !== undefined ? { chat_agent_laui: chatAgentLaui } : {}),
      ...(chatConnectionLaui !== undefined ? { chat_connection_laui: chatConnectionLaui } : {}),
      ...(chatAgentName !== undefined ? { chat_agent_name: chatAgentName } : {}),
    } as unknown as Record<string, unknown>,
  });
}

export async function getMyBusinessChatConfig(): Promise<{
  chat_agent_laui: string | null;
  chat_connection_laui: string | null;
  chat_agent_name: string | null;
  chat_agent_provider: string | null;
} | null> {
  try {
    return await httpJson(API_ENDPOINTS.userMe, { method: 'GET' });
  } catch {
    return null;
  }
}
