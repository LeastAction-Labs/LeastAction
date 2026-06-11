/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem } from '@/components/browse';

export function getColumnValue(item: CatalogItem, column: string): string {
  let value: unknown = null;

  if (item.data && typeof item.data === 'object' && column in item.data) {
    value = (item.data as Record<string, unknown>)[column];
  } else if (column in item) {
    value = (item as Record<string, unknown>)[column];
  }

  if (value === null || value === undefined) {
    return '';
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '[]';
    }
    const preview = value.slice(0, 2).map(String).join(', ');
    return value.length > 2 ? `[${preview}, ...]` : `[${preview}]`;
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  const stringValue = String(value as string | number | boolean | null | undefined);
  if (stringValue.length > 100) {
    return stringValue.substring(0, 100) + '...';
  }

  return stringValue;
}

export function formatColumnName(name: string): string {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
