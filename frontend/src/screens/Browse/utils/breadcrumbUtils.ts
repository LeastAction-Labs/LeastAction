/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem, CatalogNode } from '../../../components/browse/types';

/**
 * Flatten breadcrumb API response to a root-first chain.
 * API returns items[0] = target node, with target.parents = [parent, grandparent, ...].
 */
export function flattenBreadcrumbChain(items: CatalogNode[]): CatalogNode[] {
  if (items.length === 0) return [];
  const first = items[0];
  if (!first.parents?.length) return items;
  const chain: CatalogNode[] = [first];
  let current: CatalogNode = first;
  while (current.parents?.[0]) {
    current = current.parents[0];
    chain.push(current);
  }
  return chain.reverse();
}

/**
 * Calculate the item ID to use for breadcrumb path
 */
export function getBreadcrumbItemId(
  activeFilterType: string | null,
  filteredFromItem: CatalogItem | null,
  isItemFromTable: boolean,
  lastFilteredFromItem: CatalogItem | null,
  selectedItem: CatalogItem | null,
): string | null {
  if (activeFilterType && filteredFromItem) {
    return filteredFromItem.laui;
  }

  if (isItemFromTable && lastFilteredFromItem) {
    return lastFilteredFromItem.laui;
  }

  return selectedItem?.laui ?? null;
}
