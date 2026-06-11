/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
export interface LogTreeItem {
  id: string;
  label: string;
  children?: LogTreeItem[];
  item_type?: string;
  file_type?: string;
  originalId: string;
  data?: unknown;
  isLoading?: boolean;
  path?: string;
  size?: number;
  modified?: number;
  labelStyle?: Record<string, unknown>;
}

export interface LogsApiItem {
  name: string;
  type: string;
  size?: number;
  modified?: number;
  path?: string;
}

export interface LogsListResponse {
  items: LogsApiItem[];
  directory: string;
  total_count: number;
}

export interface LogFileDetailsResponse {
  name: string;
  path: string;
  full_path: string;
  size: number;
  modified: number;
  created: number;
  extension: string;
  is_readable: boolean;
  content?: string;
  content_type?: string;
  formatted_content?: string;
  json_valid?: boolean;
  content_error?: string;
  content_reason?: string;
}
