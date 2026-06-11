/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

type PermissionResponse = {
  permission: string;
  user_laui: string | null;
  group_laui: string | null;
};

export type AccessRelationsResponse = {
  item_laui: string;
  subject_laui: string;
  subject_type: 'user' | 'group';
  subject_permission: string;
  item_permission: string;
};

// Matching your Python Pydantic Schema
type GetAccessRelationsBackendResponse = {
  access_relations: AccessRelationsResponse[];
  next_page_token: string | null;
  skip: number;
};

const API_ENDPOINTS = {
  getPermission: `${CORE_BACKEND_URL}/api/v1/access/get/permission`,
  getUsersGroups: `${CORE_BACKEND_URL}/api/v1/access/get/access_relations`,
};

export async function getUserItemPermission(
  itemLaui: string,
  userLaui: string = '',
  groupLaui: string = '',
): Promise<any> {
  const url = `${API_ENDPOINTS.getPermission}?item_laui=${encodeURIComponent(itemLaui)}&user_laui=${encodeURIComponent(userLaui)}&group_laui=${encodeURIComponent(groupLaui)}`;
  const data = await httpJson<PermissionResponse>(url, { method: 'GET' });
  return { permission: data.permission, userLaui: data.user_laui, groupLaui: data.group_laui };
}

export async function getUsersGroups(
  permission: 'own' | 'edit' | 'view',
): Promise<AccessRelationsResponse[]> {
  let allRelations: AccessRelationsResponse[] = [];
  const nextPageToken: string | null = null;
  try {
    let url = `${API_ENDPOINTS.getUsersGroups}?permission=${permission}&per_page=250`;
    if (nextPageToken) {
      url += `&page_token=${encodeURIComponent(nextPageToken)}`;
    }

    const data = await httpJson<GetAccessRelationsBackendResponse>(url, { method: 'GET' });
    if (data?.access_relations) {
      allRelations = [...allRelations, ...data.access_relations];
    }
    return [...new Map(allRelations.map((x) => [`${x.item_laui}+${x.subject_laui}`, x])).values()];
  } catch (error) {
    console.error('Error fetching paginated access relations:', error);
    return [];
  }
}
