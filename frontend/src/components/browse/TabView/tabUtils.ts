/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Shared tab utilities used by both TabView (browse) and MarketplaceItemTabView.
 * Pure functions — no React context dependencies.
 */
import React from 'react';

import { Box } from '@mui/material';

import IframeContent from '@/components/ui/IframeContent';

// ---------------------------------------------------------------------------
// Tab name normalization
// ---------------------------------------------------------------------------

/**
 * Converts a schema field name to a human-readable tab display name.
 * Handles special cases: codeblock, bashblock, Content/Data/Info.
 */
export function normalizeTabName(fieldName: string): string {
  if (fieldName === 'codeblock') return 'Codeblock';
  if (fieldName === 'bashblock') return 'Bashblock';

  let tabName = fieldName
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .trim();

  if (['Content', 'Data', 'Info'].includes(tabName)) {
    return fieldName.charAt(0).toUpperCase() + fieldName.slice(1);
  }

  // Legacy rename rules from TabView
  tabName = tabName
    .replace(/\s+Docs$/gi, ' Documentation')
    .replace(/\s+Guide$/gi, ' Guide')
    .replace(/\s+Block$/gi, ' Blocks')
    .replace(/\s+Sample$/gi, ' Samples')
    .replace(/^Install\s+/gi, 'Installation ')
    .replace(/^Guide\s+/gi, 'Guide ');

  return tabName;
}

// ---------------------------------------------------------------------------
// Tab generation
// ---------------------------------------------------------------------------

export interface GenerateTabsOpts {
  /** 'create' | 'edit' | 'view' — controls user_update_fields filtering */
  mode?: 'create' | 'edit' | 'view';
  /** When mode=edit, only show these fields */
  userUpdateFields?: string[];
  /** Base item type string, e.g. "folder.project" */
  filterType?: string;
  /** Inject a Scheduler tab for project types (view/edit mode only) */
  includeScheduler?: boolean;
  /** Inject a synthetic subtype field for folder/operator/connection types */
  includeSubtypeField?: boolean;
  incudeMarketplaceTabs?: boolean;
  /** Tab names to suppress in view mode (content shown in sidebar instead) */
  viewSidebarTabs?: string[];
}

/**
 * Generates tabs and their field lists from a schema.
 * Supports both config-driven (field.tab.name) and legacy (auto-derive) modes.
 */
export function generateTabs(
  schema: any,
  opts: GenerateTabsOpts = {},
): { tabs: string[]; tabFields: Record<string, any[]> } {
  if (!schema?.columns) return { tabs: [], tabFields: {} };

  const {
    mode = 'view',
    userUpdateFields,
    filterType = '',
    includeScheduler = false,
    includeSubtypeField = false,
    incudeMarketplaceTabs = false,
    viewSidebarTabs = [],
  } = opts;

  const tabs: string[] = [];
  const tabFields: Record<string, any[]> = {};

  const systemUpdateFields: string[] = schema?.system_update_fields ?? [];
  const userUpdateFieldsArr: string[] = userUpdateFields ?? [];
  const uniqueConstraintFields: string[] = Array.isArray(schema?.unique_constraints)
    ? schema.unique_constraints
    : [];

  // Pure system fields = in system_update_fields but NOT also in user_update_fields
  const pureSystemFields = systemUpdateFields.filter(
    (name: string) => !userUpdateFieldsArr.includes(name),
  );

  let baseColumns: any[];
  if (mode === 'create') {
    if (userUpdateFieldsArr.length > 0) {
      // Explicit allow-list: user_update_fields + unique_constraints (needed on creation)
      const createAllowList = new Set([...userUpdateFieldsArr, ...uniqueConstraintFields]);
      baseColumns = schema.columns.filter(
        (f: any) => createAllowList.has(f.name) && !pureSystemFields.includes(f.name),
      );
    } else {
      // No explicit list — show all non-system fields
      baseColumns = schema.columns.filter((f: any) => !pureSystemFields.includes(f.name));
    }
  } else if (mode === 'edit') {
    if (userUpdateFieldsArr.length) {
      baseColumns = schema.columns.filter((f: any) => userUpdateFieldsArr.includes(f.name));
    } else {
      baseColumns = schema.columns.filter(
        (f: any) => !pureSystemFields.includes(f.name) && !uniqueConstraintFields.includes(f.name),
      );
    }
  } else {
    baseColumns = schema.columns; // view
  }

  // Filter out form_excluded_fields in create/edit mode
  const formExcludedFields: string[] = schema?.form_excluded_fields ?? [];
  // *_laui reference fields are never shown — auto-set from context
  const autoContextFields = ['account_laui', 'project_laui', 'skill_laui', 'marketplace_laui'];
  const allExcluded = new Set([
    ...autoContextFields,
    ...(mode !== 'view' ? formExcludedFields : []),
  ]);
  baseColumns = baseColumns.filter((f: any) => !allExcluded.has(f.name));

  // Mark unique constraint fields as readOnly when they appear in edit mode
  const visibleColumns =
    mode === 'edit'
      ? baseColumns.map((f: any) =>
          uniqueConstraintFields.includes(f.name) ? { ...f, readOnly: true } : f,
        )
      : baseColumns;

  const hasTabConfig = visibleColumns.some((f: any) => f.tab?.name);
  const baseType = filterType.split('.')[0] || '';

  // Synthetic subtype field injected for folder/operator/connection
  const subtypeField =
    includeSubtypeField && ['folder', 'operator', 'connection'].includes(baseType)
      ? [
          {
            name: 'subtype',
            datatype: 'string',
            required: false,
            max_length: 100,
            description: 'Subtype for the item (will be appended to item_type)',
            readOnly: mode === 'view',
            tab: hasTabConfig ? { name: 'Overview', order: 3 } : undefined,
          },
        ]
      : [];

  // Synthetic field to optionally attach a config when creating a workflow folder.
  // Rendered only for folder.workflow by TabView; carries no backend meaning.
  const attachedConfigField =
    (mode === 'create' || mode === 'edit') && baseType === 'folder'
      ? [
          {
            name: 'attached_config',
            datatype: 'object',
            required: false,
            description: 'Optionally attach a config to this workflow',
            readOnly: false,
            tab: hasTabConfig ? { name: 'Overview', order: 4 } : undefined,
          },
        ]
      : [];

  // Synthetic field shown atop the Add Config form to attach an existing config
  // instead of creating a new one. UI-only — handled in handleSaveItem.
  const existingConfigField =
    mode === 'create' && baseType === 'config'
      ? [
          {
            name: 'existing_config_laui',
            datatype: 'string',
            required: false,
            description: 'Or attach an existing config instead of creating a new one',
            readOnly: false,
            ui_display_name: 'Attach Existing Config',
            tab: hasTabConfig ? { name: 'Overview', order: 0 } : undefined,
          },
        ]
      : [];

  const addToTab = (tabName: string, field: any) => {
    if (!tabs.includes(tabName)) {
      tabs.push(tabName);
      tabFields[tabName] = [];
    }
    tabFields[tabName].push(field);
  };

  if (hasTabConfig) {
    const allFields = [
      ...existingConfigField,
      ...subtypeField,
      ...attachedConfigField,
      ...visibleColumns,
    ];
    allFields.forEach((field: any) => {
      // In view mode, name is already shown in the header — skip it here
      if (field.name.toLowerCase() === 'name' && mode === 'view') return;
      const tabName = field.tab?.name ?? normalizeTabName(field.name);
      addToTab(tabName, field);
    });
    // Sort fields within each tab by tab.order
    tabs.forEach((t) => {
      tabFields[t].sort((a: any, b: any) => (a.tab?.order ?? 99) - (b.tab?.order ?? 99));
    });
  } else {
    // Legacy: name/description → Overview tab; each other field gets its own tab
    // In view mode, name is already shown in the header — exclude it to avoid duplication
    const overviewFields = visibleColumns.filter((f: any) => {
      if (f.name.toLowerCase() === 'name' && mode === 'view') return false;
      return f.name.toLowerCase() === 'name' || f.name.toLowerCase() === 'description';
    });
    const subtypeOverviewFields = [...existingConfigField, ...subtypeField, ...attachedConfigField]; // goes into Overview too
    if (overviewFields.length > 0 || subtypeOverviewFields.length > 0) {
      addToTab('Overview', null); // ensure tab exists
      tabFields['Overview'] = [];
      [...overviewFields, ...subtypeOverviewFields].forEach((f) => tabFields['Overview'].push(f));
    }

    visibleColumns
      .filter((f: any) => f.name.toLowerCase() !== 'name' && f.name.toLowerCase() !== 'description')
      .sort((a: any, b: any) => {
        if (a.required && !b.required) return -1;
        if (!a.required && b.required) return 1;
        return 0;
      })
      .forEach((field: any) => {
        addToTab(normalizeTabName(field.name), field);
      });
  }

  // Scheduler tab for projects in view/edit mode
  if (includeScheduler && filterType.includes('project') && mode === 'view') {
    if (!tabs.includes('Scheduler')) {
      tabs.push('Scheduler');
      tabFields['Scheduler'] = [];
    }
  }

  if (incudeMarketplaceTabs) {
    if (!tabs.includes('Reviews')) {
      tabs.push('Reviews');
      tabFields['Reviews'] = [];
      tabs.push('Issues');
      tabFields['Issues'] = [];
    }
  }

  // Remove tabs that are shown in the sidebar for view mode
  if (mode === 'view' && viewSidebarTabs.length > 0) {
    for (const sidebarTab of viewSidebarTabs) {
      const idx = tabs.indexOf(sidebarTab);
      if (idx !== -1) {
        tabs.splice(idx, 1);
        delete tabFields[sidebarTab];
      }
    }
  }

  return { tabs, tabFields };
}

// ---------------------------------------------------------------------------
// FormData processing
// ---------------------------------------------------------------------------

/**
 * Prepares item data for use in a form or view:
 * - Merges nested `data` fields into top level
 * - Parses folder_metadata JSON string → object
 * - Extracts subtype from item_type
 */
export function processFormData(item: Record<string, any>): Record<string, any> {
  const processed: Record<string, any> = { ...item };

  // Merge nested data object
  if (processed.data && typeof processed.data === 'object' && !Array.isArray(processed.data)) {
    Object.entries(processed.data as Record<string, unknown>).forEach(([k, v]) => {
      if (processed[k] === undefined || processed[k] === null || processed[k] === '') {
        processed[k] = v;
      }
    });
  }

  // Parse folder_metadata if stored as JSON string
  if (processed.folder_metadata && typeof processed.folder_metadata === 'string') {
    try {
      processed.folder_metadata = JSON.parse(processed.folder_metadata);
    } catch {
      // Keep as string if invalid JSON
    }
  }

  // Extract subtype from item_type
  if (processed.item_type) {
    const parts = String(processed.item_type).split('.');
    processed.subtype = parts.length > 1 ? parts.slice(1).join('.') : '';
  }

  return processed;
}

// ---------------------------------------------------------------------------
// HTML tab renderer
// ---------------------------------------------------------------------------

/**
 * Renders an HTML tab safely — content is isolated in a sandboxed iframe.
 */
export function renderHtmlTab(item: Record<string, any>): React.ReactNode {
  const rawHtml: string = item?.html || item?.data?.html || '';

  if (!rawHtml) {
    return React.createElement(
      Box,
      { sx: { p: 3, color: 'var(--text-secondary)', fontSize: '12px' } },
      'No content.',
    );
  }

  return React.createElement(
    Box,
    { sx: { height: '100%', boxSizing: 'border-box' } },
    React.createElement(IframeContent, { content: rawHtml, height: '100%' }),
  );
}
