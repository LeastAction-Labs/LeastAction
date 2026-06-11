/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { FullItemData } from '@/components/browse/types';

export interface ActionDef {
  name: string;
  action_variables: Record<string, any>;
  marketplace_laui?: string;
}

export interface TaskMeta {
  name: string;
  frequency?: string;
  operator_name: string;
  connection_name: string;
  marketplace_laui?: string;
  partition?: string;
  config_name?: string | string[];
  start_date?: string;
  end_date?: string;
  over_ride?: boolean;
  config?: Record<string, any>;
  actions?: {
    pre_actions?: ActionDef[];
    running_actions?: ActionDef[];
    post_actions?: ActionDef[];
  };
}

export interface PayloadItem {
  filename: string;
  content: string;
}

export interface ParsedPayload {
  filename: string;
  meta: TaskMeta | null;
  payload: string;
}

export interface DependencyStatus {
  name: string;
  type: 'operator' | 'connection' | 'action' | 'config';
  found: boolean;
  laui?: string;
}

export interface UsecaseImportModalData {
  itemData?: FullItemData;
  isOpen: boolean;
}

export interface TaskCreationResult {
  name: string;
  success: boolean;
  error?: string;
}

export interface PayloadDepGroup {
  payloadNames: string[];
  operator_name: string;
  connection_name: string;
  config_names: string[];
  action_names: string[];
}
