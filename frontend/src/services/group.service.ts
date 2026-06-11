/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// services/group.service.ts
import type { GroupDetailsData } from '@/components/browse/Groups/GroupDetails';
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

const API_ENDPOINTS = {
  group: {
    create: `${CORE_BACKEND_URL}/api/v1/group/create`,
    get: `${CORE_BACKEND_URL}/api/v1/group/get`,
    getById: (laui: string) => `${CORE_BACKEND_URL}/api/v1/group/get/${laui}`,
    search: `${CORE_BACKEND_URL}/api/v1/group/search`,
  },
};

interface GroupData {
  name: string;
  description: string;
  members: string[]; // Frontend: "Members" -> Backend: "viewers"
  admins: string[]; // Frontend: "Admins" -> Backend: "editors"
}

export interface GroupItem {
  id: string;
  name: string;
}

export interface GroupsResponse {
  groups: GroupItem[];
  next_page_token: string;
}

export interface UserInfo {
  laui: string;
  email: string | null;
}

export interface GroupDetails {
  name: string;
  description: string;
  admins: string[];
  members: string[];
  owners: string[];
  laui: string;
}

export type Relation = 'owners' | 'editors' | 'viewers';

export async function createGroup(groupData: GroupData): Promise<any> {
  const backendPayload: Record<string, unknown> = {
    name: groupData.name,
    description: groupData.description,
    access_patch: {
      add: {
        viewers: groupData.members.reduce(
          (acc, member) => {
            acc[member] = '';
            return acc;
          },
          {} as Record<string, string>,
        ),
        editors: groupData.admins.reduce(
          (acc, admin) => {
            acc[admin] = '';
            return acc;
          },
          {} as Record<string, string>,
        ),
        owners: {},
      },
      remove: {
        viewers: {},
        editors: {},
        owners: {},
      },
    },
  };

  return await httpJson<any>(API_ENDPOINTS.group.create, {
    method: 'POST',
    body: backendPayload as any,
  });
}

export async function getGroups(relation: Relation): Promise<GroupsResponse> {
  return await httpJson<GroupsResponse>(`${API_ENDPOINTS.group.get}?relation=${relation}`, {
    method: 'GET',
  });
}

export async function getGroup(groupLaui: string): Promise<GroupDetailsData> {
  return await httpJson<GroupDetailsData>(API_ENDPOINTS.group.getById(groupLaui), {
    method: 'GET',
  });
}

export async function updateGroup(
  name: string,
  description: string,
  accessPatch: {
    add: {
      viewers: Record<string, string>;
      editors: Record<string, string>;
      owners: Record<string, string>;
    };
    remove: {
      viewers: Record<string, string>;
      editors: Record<string, string>;
      owners: Record<string, string>;
    };
  },
): Promise<any> {
  const backendPayload = {
    name,
    description,
    access_patch: accessPatch,
  };

  return await httpJson<any>(API_ENDPOINTS.group.create, {
    method: 'POST',
    body: backendPayload as any,
  });
}

export async function searchGroups(payload: any) {
  if (!('page' in payload)) payload['page'] = 1;
  if (!('page' in payload)) payload['per_page'] = 10;
  return await httpJson<any>(API_ENDPOINTS.group.search, {
    method: 'POST',
    body: payload,
  });
}
