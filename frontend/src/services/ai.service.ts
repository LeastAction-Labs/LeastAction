/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import type { AIGenerationResponse, Connection, Payload, Workflow } from '../components/ai/types';
import { httpJson } from './api';

const API_ENDPOINTS = {
  ai: {
    generate: `${CORE_BACKEND_URL}/api/v1/ai/generate`,
    chat: `${CORE_BACKEND_URL}/api/v1/ai/agent`,
  },
  catalog: {
    get: `${CORE_BACKEND_URL}/api/v1/catalog/get`,
  },
};

export interface ConnectionItem {
  laui: string;
  name: string;
  item_type: string;
  provider?: string;
  data?: any;
}

// Get root items with full hierarchy
export async function getRootItems(): Promise<any> {
  const url = `${API_ENDPOINTS.catalog.get}?is_root=true&d&per_page=10&depth=5`;
  //console.log('Fetching root items from:', url);

  try {
    const data = await httpJson<any>(url, { method: 'GET' });
    return data;
  } catch (error) {
    console.error('Error fetching root items:', error);
    throw error;
  }
}

// Fetch Connections by Provider using two-step API call
export async function fetchConnectionsByProvider(provider: string): Promise<ConnectionItem[]> {
  //console.log('Fetching connections for provider:', provider);

  try {
    // Step 1: Get all connections
    const allConnections = await fetchAllConnections();

    // Step 2: Filter by provider
    const filteredConnections: ConnectionItem[] = allConnections
      .filter((conn: Connection) => {
        return conn.item_type === `connection.${provider}`;
      })
      .map((conn: Connection) => ({
        laui: conn.laui,
        name: conn.name || `Unnamed ${provider} Connection`,
        item_type: conn.item_type,
        provider: provider,
        data: conn.data,
      }));

    //console.log(`Found ${filteredConnections.length} connections for ${provider}:`, filteredConnections);
    return filteredConnections;
  } catch (error) {
    console.error('Error fetching connections by provider:', error);
    throw error;
  }
}

// AI Generation
export async function generateAIContent(data: {
  prompt: string;
  chat_laui: string;
  item_type: string;
  ai_provider: string;
  include_guide_doc: boolean;
  include_install_guide: boolean;
  messages?: { role: string; content: string }[];
  generated_content?: Record<string, any>;
  skill_content?: string;
  session_id?: string;
  connection_laui?: string;
}): Promise<AIGenerationResponse> {
  //console.log('Generating AI content with data:', data);

  try {
    const response = await httpJson<AIGenerationResponse>(API_ENDPOINTS.ai.generate, {
      method: 'POST',
      body: data,
    });
    //console.log('AI generation response:', response);
    return response;
  } catch (error) {
    console.error('Error generating AI content:', error);
    throw error;
  }
}

// AI Chat (conversational with optional MCP tool calling)
export async function chatWithAI(
  data: {
    prompt: string;
    chat_laui: string;
    messages?: { role: string; content: string }[];
    connection_laui?: string;
    enable_tools?: boolean;
    skill_content?: string;
  },
  signal?: AbortSignal,
): Promise<{ message: string; tool_calls_made?: string[]; content_type?: string }> {
  try {
    const response = await httpJson<{
      message: string;
      tool_calls_made?: string[];
      content_type?: string;
    }>(API_ENDPOINTS.ai.chat, {
      method: 'POST',
      body: data,
      signal,
    });
    return response;
  } catch (error) {
    console.error('Error in AI chat:', error);
    throw error;
  }
}

// Fetch All Connections - optionally filter by project
export async function fetchAllConnections(project_laui?: string): Promise<Connection[]> {
  //console.log('Fetching all connections', project_laui ? `for project: ${project_laui}` : '');

  try {
    // Fetch root items which includes the full hierarchy
    const rootData = await getRootItems();
    //console.log('Root data for connections:', JSON.stringify(rootData, null, 2));

    let projectItem: any;

    if (project_laui) {
      // Find the specific project by laui in the hierarchy
      const accountItem = rootData.items?.[0];
      projectItem = accountItem?.children?.find(
        (child: any) => (child.item?.laui || child.laui) === project_laui,
      );
      //console.log('Found project item for laui:', project_laui, projectItem);
    } else {
      // Use the first project
      const accountItem = rootData.items?.[0];
      projectItem = accountItem?.children?.find(
        (child: any) => child.item?.item_type === 'folder.project',
      );
      //console.log('Using first project item:', projectItem);
    }

    if (!projectItem) {
      //console.log('Project item not found');
      return [];
    }

    // Find folder.connection in project children
    const folderConnection = projectItem.children?.find(
      (child: any) => child.item?.item_type === 'folder.connection',
    );

    if (!folderConnection) {
      //console.log('folder.connection not found in project children');
      return [];
    }

    const folderConnectionLaui = folderConnection.item.laui;
    //console.log('folder.connection laui:', folderConnectionLaui);

    // Get all connections under folder.connection using parent_or_child=child
    const queryParams = new URLSearchParams({
      d: '',
      per_page: '10',
      depth: '5',
      item_laui: folderConnectionLaui,
      item_type: 'connection',
      parent_or_child: 'child',
    });

    const url = `${API_ENDPOINTS.catalog.get}?${queryParams.toString()}`;
    //console.log('Fetching connections from:', url);

    const data = await httpJson<any>(url, { method: 'GET' });
    //console.log('Connections response:', JSON.stringify(data, null, 2));

    // Map to Connection format
    const connections: Connection[] = (data.items || []).map((item: any) => ({
      laui: item.item?.laui || item.laui,
      name: item.item?.name || item.name || 'Unnamed Connection',
      item_type: item.item?.item_type || item.item_type,
      provider: (item.item?.item_type || item.item_type)?.replace('connection.', '') || 'unknown',
      data: item.item || item,
    }));

    //console.log(`Found ${connections.length} connections:`, connections);
    return connections;
  } catch (error) {
    console.error('Error fetching all connections:', error);
    throw error;
  }
}

// Fetch All Payloads
export async function fetchAllPayloads(): Promise<Payload[]> {
  const url = `${API_ENDPOINTS.catalog.get}?item_type=payload`;
  //console.log('Fetching payloads from:', url);

  try {
    const data = await httpJson<{ items: any[] }>(url, { method: 'GET' });
    const payloads: Payload[] = (data.items || []).map((item) => ({
      laui: item.laui,
      name: item.name || item.data?.name || 'Unnamed Payload',
      item_type: item.item_type,
      data: item.data,
    }));
    //console.log('Fetched payloads:', payloads);
    return payloads;
  } catch (error) {
    console.error('Error fetching payloads:', error);
    throw error;
  }
}

// Fetch Workflow Folders - optionally filter by project
export async function fetchWorkflows(project_laui?: string): Promise<Workflow[]> {
  //console.log('Fetching workflow folders', project_laui ? `for project: ${project_laui}` : '');

  try {
    // Fetch root items which includes the full hierarchy
    const rootData = await getRootItems();
    //console.log('Root data for workflow folders:', JSON.stringify(rootData, null, 2));

    let projectItem: any;

    if (project_laui) {
      // Find the specific project by laui in the hierarchy
      const accountItem = rootData.items?.[0];
      projectItem = accountItem?.children?.find(
        (child: any) => (child.item?.laui || child.laui) === project_laui,
      );
      //console.log('Found project item for laui:', project_laui, projectItem);
    } else {
      // Use the first project
      const accountItem = rootData.items?.[0];
      projectItem = accountItem?.children?.find(
        (child: any) => child.item?.item_type === 'folder.project',
      );
      //console.log('Using first project item:', projectItem);
    }

    if (!projectItem) {
      //console.log('Project item not found');
      return [];
    }

    // Find folder.workflow items in project children
    const workflowFolders: Workflow[] = [];

    projectItem.children?.forEach((child: any) => {
      const itemType = child.item?.item_type || child.item_type;
      if (itemType === 'folder.workflow') {
        workflowFolders.push({
          laui: child.item?.laui || child.laui,
          name: child.item?.name || child.name || 'Unnamed Workflow Folder',
          item_type: itemType,
          data: child.item || child,
        });
      }
    });

    //console.log(`Found ${workflowFolders.length} workflow folders:`, workflowFolders);
    return workflowFolders;
  } catch (error) {
    console.error('Error fetching workflow folders:', error);
    // Return empty array instead of throwing to allow the modal to work
    //console.log('Returning empty workflow folders array due to error');
    return [];
  }
}

// Fetch Projects - optionally filter by account
export async function fetchProjects(
  account_laui?: string,
): Promise<Array<{ laui: string; name: string; item_type: string }>> {
  //console.log('Fetching projects', account_laui ? `for account: ${account_laui}` : '');

  try {
    // Fetch root items which includes accounts and their children (projects)
    const rootData = await getRootItems();
    //console.log('Root data received:', JSON.stringify(rootData, null, 2));

    let accountItem: any;

    if (account_laui) {
      // Find the specific account by laui
      accountItem = rootData.items?.find(
        (item: any) => (item.item?.laui || item.laui) === account_laui,
      );
      //console.log('Found account item for laui:', account_laui, accountItem);
    } else {
      // Use the first account
      accountItem = rootData.items?.[0];
      //console.log('Using first account item:', accountItem);
    }

    if (!accountItem) {
      //console.log('Account item not found');
      return [];
    }

    // Get projects from account children
    const projects =
      accountItem.children?.filter((child: any) => {
        const itemType = child.item?.item_type || child.item_type;
        //console.log('Checking child item_type:', itemType);
        return itemType === 'folder.project';
      }) || [];

    //console.log('Filtered projects from children:', JSON.stringify(projects, null, 2));

    // Map to project format
    const projectList = projects.map((project: any) => ({
      laui: project.item?.laui || project.laui,
      name: project.item?.name || project.name || 'Unnamed Project',
      item_type: project.item?.item_type || project.item_type,
    }));

    //console.log(`Found ${projectList.length} projects:`, projectList);
    return projectList;
  } catch (error) {
    console.error('Error fetching projects:', error);
    throw error;
  }
}

// Fetch Accounts
export async function fetchAccounts(): Promise<
  Array<{ laui: string; name: string; item_type: string }>
> {
  //console.log('Fetching accounts');

  try {
    // Get root items with full hierarchy
    const rootData = await getRootItems();

    // Get all account items (folder.account)
    const accounts = (rootData.items || [])
      .filter((item: any) => {
        const itemType = item.item?.item_type || item.item_type;
        return itemType === 'folder.account';
      })
      .map((account: any) => ({
        laui: account.item?.laui || account.laui,
        name: account.item?.name || account.name || 'Unnamed Account',
        item_type: account.item?.item_type || account.item_type,
      }));

    //console.log(`Found ${accounts.length} accounts:`, accounts);
    return accounts;
  } catch (error) {
    console.error('Error fetching accounts:', error);
    throw error;
  }
}

// Save AI Generated Item
export async function saveAIGeneratedItem(itemData: any): Promise<any> {
  const { createCatalogItem } = await import('./catalog.service');
  return await createCatalogItem(itemData);
}

// Save Manual Item
export async function saveManualItem(itemData: any): Promise<any> {
  const { createCatalogItem } = await import('./catalog.service');
  return await createCatalogItem(itemData);
}
