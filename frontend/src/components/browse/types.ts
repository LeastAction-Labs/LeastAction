/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// frontend/src/components/Browse/types.ts

export type CatalogItem = {
  laui: string;
  name: string;
  item_type: string;
  parent_laui?: string | null;
  project_laui?: string | null;
  is_root?: boolean;
  data?: { name?: string; description?: string } | null;
  description?: string;
  supported_types?: string[];
  deleted_at?: string;
  permission: string;
  updated_at?: string | null;
  skill_laui?: string;
  notes?: string;
  image_url?: string;
  tags?: string[];
  category?: string;
  division?: string;
  publisher?: string;
  verified?: boolean;
  is_published?: boolean;
  marketplace_laui?: string;
  version_compatibility?: { core?: string[]; python?: string; la_interface?: string };
  version_details?: { deprecated?: boolean; deprecated_at?: string; [key: string]: unknown };
};

export type FormMode = 'create' | 'edit' | 'view' | null;

export interface FormSchema {
  columns: FormSchemaColumn[];
  projection_fields?: string[];
  unique_constraints?: string[];
  indexes?: unknown[];
  user_update_fields?: string[];
  system_update_fields?: string[];
  form_excluded_fields?: string[];
}
export interface TabViewProps {
  schema: FormSchema;
  filterType: string;
  availableSubtypes?: string[];
  onSave?: (data: any) => void;
  onCancel: () => void;
  mode: FormMode;
  initialData?: any;
  itemData?: any; // For view mode
}
export interface FormSchemaColumn {
  name: string;
  datatype: string;
  required?: boolean;
  min_length?: number;
  max_length?: number;
  regex?: string;
  description?: string;
  default?: unknown;
  items?: string;
  editorType?: 'textbox' | 'monaco';
  editorMonacoFormat?:
    | 'auto'
    | 'python'
    | 'json'
    | 'markdown'
    | 'javascript'
    | 'html'
    | 'css'
    | 'yaml'
    | 'text';
  enum_values?: string[];
  sample_placeholder?: Record<string, unknown>;
}

export interface FormField {
  name: string;
  datatype: string;
  required: boolean;
  min_length?: number;
  max_length?: number;
  regex?: string;
  description: string;
  items?: string;
}

export type CatalogNode = {
  item: CatalogItem;
  children: CatalogNode[];
  parents: CatalogNode[];
};

/** Matches backend PaginationResponse (src/core/api/common.py) */
export type Pagination = {
  current_page: number;
  per_page: number;
  has_next: boolean;
  next_page_token?: string | null;
  /** Derived: true when current_page > 1 */
  has_previous?: boolean;
};

export type ApiResponse = {
  items: CatalogNode[];
  pagination: Pagination;
};

// Comprehensive type for full item data from API when fetching by ID
export type FullItemData = {
  laui: string;
  name: string;
  item_type: string;
  parent_laui?: string | null;
  permission: string;
  is_root?: boolean;
  supported_types?: string[];
  created_at?: string | null;
  updated_at?: string | null;
  deleted_at?: string | null;
  version?: number;
  folder_metadata?: {
    cron_status?: string;
    latest_heartbeat?: string;
    [key: string]: unknown;
  };
  version_compatibility?: {
    core?: string[];
    python?: string;
    la_interface?: string;
  };
  version_details?: {
    version?: string;
    released_at?: string;
    changelog?: string;
    versioning_mode?: 'implicit' | 'explicit';
    channel?: string;
    deprecated?: boolean;
    deprecated_at?: string;
    deprecated_reason?: string;
    [key: string]: unknown;
  };
  image_url?: string;
  tags?: string[];
  category?: string;
  division?: string;
  publisher?: string;
  verified?: boolean;
  is_published?: boolean;
  has_unpublished_changes?: boolean;
  marketplace_laui?: string;
  [key: string]: unknown; // Allow additional fields from item_type.json schemas
};

export type ChildItem = CatalogItem;
