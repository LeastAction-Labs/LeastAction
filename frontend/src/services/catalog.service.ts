/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// services/catalog.services.ts
import { CORE_BACKEND_URL, MARKETPLACE_URL } from '@/config/urls';

import type { ApiResponse, CatalogNode, FullItemData, Pagination } from '../components/browse';
import type { JsonRecord } from './api';
import { httpJson, httpJsonWithSession } from './api';
import type { TaskRunResponse } from './task.service';
import { preprocessItemData } from './utils';

export type CatalogNodesWithPagination = {
  items: CatalogNode[];
  pagination: Pagination;
};

const API_ENDPOINTS = {
  catalog: {
    get: `${CORE_BACKEND_URL}/api/v1/catalog/get`,
    create: `${CORE_BACKEND_URL}/api/v1/catalog/create`,
    anonymousCreate: `${CORE_BACKEND_URL}/api/v1/catalog/anonymous/create`,
    update: `${CORE_BACKEND_URL}/api/v1/catalog/create`,
    validate: `${CORE_BACKEND_URL}/api/v1/catalog/validate`,
    delete: `${CORE_BACKEND_URL}/api/v1/catalog/delete`,
    createLink: `${CORE_BACKEND_URL}/api/v1/catalog/create/link`,
    search: `${CORE_BACKEND_URL}/api/v1/catalog/search`,
    supportedTypes: `${CORE_BACKEND_URL}/api/v1/catalog/item-types/supported-types`,
    restore: `${CORE_BACKEND_URL}/api/v1/catalog/restore`,
    marketplaceGet: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/get`,
    marketplaceCreate: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/create`,
    marketplaceAnonymousCreate: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/anonymous/create`,
    marketplaceDelete: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/delete`,
    marketplaceRestore: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/restore`,
    marketplaceSearch: `${MARKETPLACE_URL}/api/v1/marketplace/catalog/search`,
  },
  task: {
    run: `${CORE_BACKEND_URL}/api/v1/task/run`,
  },
  action: {
    run: `${CORE_BACKEND_URL}/api/v1/action/run`,
  },
};

const DEFAULT_PAGINATION: Pagination = {
  current_page: 1,
  per_page: 10,
  has_next: false,
  has_previous: false,
};

function normalizePagination(
  data: ApiResponse,
  page: number,
  perPage: number,
): CatalogNodesWithPagination {
  const items = Array.isArray(data.items) ? data.items : [];
  const pagination: Pagination = data.pagination
    ? {
        ...data.pagination,
        has_previous: (data.pagination.current_page ?? page) > 1,
      }
    : { ...DEFAULT_PAGINATION, current_page: page, per_page: perPage };
  return { items, pagination };
}

export async function getRootCatalogNodes(
  marketplace: boolean = false,
  page: number = 1,
  perPage: number = 10,
): Promise<CatalogNodesWithPagination> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  const url = `${base_url}?is_root=true&page=${page}&per_page=${perPage}`;
  const data = await httpJson<ApiResponse>(url, { method: 'GET' });
  return normalizePagination(data, page, perPage);
}

export async function getChildCatalogNodes(
  itemId: string,
  itemPermission: string,
  marketplace: boolean = false,
  page: number = 1,
  perPage: number = 10,
  itemType?: string,
): Promise<CatalogNodesWithPagination> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  let url = `${base_url}?item_laui=${encodeURIComponent(
    itemId,
  )}&parent_or_child=child&item_permission=${encodeURIComponent(itemPermission)}&page=${page}&per_page=${perPage}`;
  if (itemType) url += `&item_type=${encodeURIComponent(itemType)}`;
  const data = await httpJson<ApiResponse>(url, { method: 'GET' });
  return normalizePagination(data, page, perPage);
}

export async function getChildCatalogNodesByType(
  itemId: string,
  itemType: string,
  itemPermission: string,
  marketplace: boolean = false,
  page: number = 1,
  perPage: number = 10,
  sortBy?: string,
  sortOrder?: 'asc' | 'desc',
  filterState?: string,
): Promise<CatalogNodesWithPagination> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  let url = `${base_url}?item_laui=${encodeURIComponent(
    itemId,
  )}&parent_or_child=child&item_type=${encodeURIComponent(itemType)}&item_permission=${encodeURIComponent(itemPermission)}&page=${page}&per_page=${perPage}`;
  if (sortBy)
    url += `&sort_by=${encodeURIComponent(sortBy)}&sort_order=${encodeURIComponent(sortOrder ?? 'asc')}`;
  if (filterState) url += `&filter_state=${encodeURIComponent(filterState)}`;
  const data = await httpJson<ApiResponse>(url, { method: 'GET' });
  return normalizePagination(data, page, perPage);
}

export async function getParentCatalogNodes(
  itemId: string,
  itemPermission: string,
  marketplace: boolean = false,
  page: number = 1,
  perPage: number = 10,
): Promise<CatalogNodesWithPagination> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  const url = `${base_url}?item_laui=${encodeURIComponent(
    itemId,
  )}&parent_or_child=parent&item_permission=${encodeURIComponent(itemPermission)}&page=${page}&per_page=${perPage}`;
  const data = await httpJson<ApiResponse>(url, { method: 'GET' });
  return normalizePagination(data, page, perPage);
}

export async function getParentCatalogNodesByType(
  itemId: string,
  itemType: string,
  itemPermission: string,
  marketplace: boolean = false,
  page: number = 1,
  perPage: number = 10,
): Promise<CatalogNodesWithPagination> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  const url = `${base_url}?item_laui=${encodeURIComponent(
    itemId,
  )}&parent_or_child=parent&item_type=${encodeURIComponent(itemType)}&item_permission=${encodeURIComponent(itemPermission)}&page=${page}&per_page=${perPage}`;
  const data = await httpJson<ApiResponse>(url, { method: 'GET' });
  return normalizePagination(data, page, perPage);
}

export async function getCatalogItemById(
  itemId: string,
  marketplace: boolean = false,
): Promise<FullItemData> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  const url = `${base_url}?item_laui=${encodeURIComponent(itemId)}`;

  try {
    const data = await httpJson<FullItemData>(url, { method: 'GET' });
    return data;
  } catch (error) {
    console.error('Error fetching catalog item:', error);
    throw error;
  }
}

export function getBreadcrumbString(catalogNode: CatalogNode) {
  let currentNode: CatalogNode | undefined = catalogNode;
  let result = '';
  while (currentNode) {
    result = '/' + currentNode.item.name + result;
    currentNode = currentNode.parents[0];
  }
  return result;
}

export async function getBreadcrumbs(
  itemId: string,
  marketplace: boolean = false,
): Promise<ApiResponse> {
  const base_url = marketplace ? API_ENDPOINTS.catalog.marketplaceGet : API_ENDPOINTS.catalog.get;
  const url = `${base_url}?item_laui=${encodeURIComponent(itemId)}&parent_or_child=parent&depth=10`;
  try {
    const data = await httpJson<ApiResponse>(url, { method: 'GET' });
    return data;
  } catch (error) {
    console.error('Error fetching catalog item:', error);
    throw error;
  }
}

export async function createCatalogItem(itemData: any, marketplace: boolean = false): Promise<any> {
  const cleanedData = await preprocessItemData(itemData);
  const url = marketplace ? API_ENDPOINTS.catalog.marketplaceCreate : API_ENDPOINTS.catalog.create;
  return await httpJson<any>(url, {
    method: 'POST',
    body: cleanedData,
  });
}

export async function createAnonymousCatalogItem(
  itemData: any,
  marketplace: boolean = false,
): Promise<any> {
  const cleanedData = await preprocessItemData(itemData);
  const url = marketplace
    ? API_ENDPOINTS.catalog.marketplaceAnonymousCreate
    : API_ENDPOINTS.catalog.anonymousCreate;
  return await httpJson<any>(url, {
    method: 'POST',
    body: cleanedData,
  });
}

export async function deleteCatalogItem(
  itemLaui: string,
  parentLaui: string,
  marketplace: boolean = false,
): Promise<any> {
  try {
    const requestBody: any = {
      item_laui: itemLaui,
      parent_laui: parentLaui,
    };

    const url = marketplace
      ? API_ENDPOINTS.catalog.marketplaceDelete
      : API_ENDPOINTS.catalog.delete;

    return await httpJson<any>(url, {
      method: 'POST',
      body: requestBody,
    });
  } catch (error) {
    console.error('Error in deleteCatalogItem:', error);
    throw error;
  }
}

export async function createCatalogLink(linkData: any): Promise<any> {
  return await httpJson<any>(API_ENDPOINTS.catalog.createLink, {
    method: 'POST',
    body: linkData,
  });
}

export async function runAction(actionData: any, preSessionId?: string): Promise<TaskRunResponse> {
  //console.log('Running action with data:', actionData);
  if (!actionData.item_type) actionData.item_type = 'action';
  const sessionId = preSessionId || crypto.randomUUID();
  try {
    const { data } = await httpJsonWithSession<TaskRunResponse>(API_ENDPOINTS.action.run, {
      method: 'POST',
      body: actionData,
      headers: { 'X-Session-ID': sessionId },
    });
    //console.log('Action run response:', data, 'Session ID:', sessionId);
    return { ...data, session_id: sessionId };
  } catch (error) {
    console.error('Error running action:', error);
    throw error;
  }
}

export interface SearchCatalogFilters {
  account_laui?: string;
  project_laui?: string;
  parent_laui?: string;
  get_by_pk?: boolean;
  [key: string]: string | string[] | boolean | undefined;
}

export async function searchCatalogItems(
  itemType?: string,
  marketplace: boolean = false,
  opts?: { filters?: SearchCatalogFilters; perPage?: number; page?: number; projection?: string[] },
): Promise<any> {
  const url = marketplace ? API_ENDPOINTS.catalog.marketplaceSearch : API_ENDPOINTS.catalog.search;
  try {
    const item_filter: Record<string, string | string[] | boolean> = itemType
      ? { item_type: itemType }
      : {};
    if (opts?.filters) {
      for (const [k, v] of Object.entries(opts.filters)) {
        if (v != null && v !== '' && !(Array.isArray(v) && v.length === 0)) item_filter[k] = v;
      }
    }
    const body: JsonRecord = {
      item_filter,
      projection: { include: opts?.projection ?? ['name', 'action_variables'] },
      pagination: { per_page: opts?.perPage ?? 10, page: opts?.page ?? 1 },
    };
    const data = await httpJson<any>(url, {
      method: 'POST',
      body,
    });
    return data ?? { items: [] };
  } catch (error) {
    console.error('Error searching catalog items:', error);
    throw error;
  }
}

export async function searchCatalogLinks(filters: Record<string, string>): Promise<any> {
  const url = API_ENDPOINTS.catalog.search;
  try {
    const body: JsonRecord = {
      link_filter: filters,
    };
    const data = await httpJson<any>(url, {
      method: 'POST',
      body,
    });
    return data ?? { links: [] };
  } catch (error) {
    console.error('Error searching catalog items:', error);
    throw error;
  }
}

export async function getSupportedTypes(itemType: string): Promise<{
  supported_children_types: string[];
  supported_parent_types: string[];
}> {
  const url = `${API_ENDPOINTS.catalog.supportedTypes}?item_type=${encodeURIComponent(itemType)}`;
  try {
    const data = await httpJson<{
      supported_children_types: string[];
      supported_parent_types: string[];
    }>(url, { method: 'GET' });
    return data ?? { supported_children_types: [], supported_parent_types: [] };
  } catch (error) {
    console.error('Error fetching supported types:', error);
    return { supported_children_types: [], supported_parent_types: [] };
  }
}

export async function bootstrapProject(projectLaui: string): Promise<any> {
  return await httpJson<any>(
    `${CORE_BACKEND_URL}/api/v1/catalog/bootstrap?project_laui=${encodeURIComponent(projectLaui)}`,
    { method: 'POST' },
  );
}

export async function restoreItem(itemLaui: string, marketplace: boolean = false): Promise<any> {
  const url = marketplace
    ? API_ENDPOINTS.catalog.marketplaceRestore
    : API_ENDPOINTS.catalog.restore;
  try {
    const data = await httpJson<any>(url + `/${itemLaui}`, {
      method: 'POST',
    });
    return data;
  } catch (error) {
    console.error('Error restoring item:', error);
    throw error;
  }
}
