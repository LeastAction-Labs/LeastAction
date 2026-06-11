/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem } from '@/components/browse/types';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { getChildCatalogNodes, getChildCatalogNodesByType } from '@/services/catalog.service';

import {
  appendNodeChildren,
  deduplicateItemsByLaui,
  extractItems,
  updateNodeChildren,
} from '../utils/catalogTreeUtils';

/**
 * Provides actions for managing catalog data
 */
export function useCatalogActions(
  findItem: (targetId: string) => CatalogItem | null,
  findPath: (targetId: string | null) => CatalogItem[],
) {
  const { catalogType } = useGlobal();
  const { catalogState } = useCatalog();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const {
    setItems,
    setError,
    setExpandedItems,
    setSelectedItem,
    loadedChildren,
    setLoadedChildren,
    setLoadingChildren,
    setFilteredItemsByType,
    setFilteredItemsPagination,
    setActiveFilterType,
    setFilteredFromItem,
    setLastFilterType,
    setLastFilteredFromItem,
    setLastFilteredItems,
    setIsItemFromTable,
    setOpenedFolder,
    childrenPagination,
    setChildrenPagination,
  } = catalogState;

  // Load children of a node
  const loadChildren = async (itemId: string, itemPermission: string, force = false) => {
    if (!force && loadedChildren.has(itemId)) return;
    try {
      setLoadingChildren((prev) => new Set(prev).add(itemId));
      const { items: children, pagination } = await getChildCatalogNodes(
        itemId,
        itemPermission,
        isMarketplaceCatalog,
        1,
        10,
        'folder',
      );
      setItems((prevItems) => updateNodeChildren(prevItems, itemId, children));
      setChildrenPagination((prev) => ({ ...prev, [itemId]: pagination }));
      setLoadedChildren((prev) => new Set(prev).add(itemId));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to load children';
      setError(message);
    } finally {
      setLoadingChildren((prev) => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });
    }
  };

  // Load the next page of children and append to existing
  const loadMoreChildren = async (itemId: string, itemPermission: string) => {
    const currentPagination = childrenPagination[itemId];
    if (!currentPagination?.has_next) return;
    const nextPage = currentPagination.current_page + 1;
    try {
      setLoadingChildren((prev) => new Set(prev).add(itemId));
      const { items: newChildren, pagination } = await getChildCatalogNodes(
        itemId,
        itemPermission,
        isMarketplaceCatalog,
        nextPage,
        10,
        'folder',
      );
      setItems((prevItems) => appendNodeChildren(prevItems, itemId, newChildren));
      setChildrenPagination((prev) => ({ ...prev, [itemId]: pagination }));
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to load more children';
      setError(message);
    } finally {
      setLoadingChildren((prev) => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });
    }
  };

  // Expand folders in path to selected item (without collapsing others)
  const expandPathToItem = async (targetItemId: string | null, knownPath?: CatalogItem[]) => {
    if (!targetItemId) return;

    const path = knownPath && knownPath.length > 0 ? knownPath : findPath(targetItemId);
    if (path.length === 0) return;

    // Expand all items in the path (excluding the target item itself)
    const pathToExpand = path.slice(0, -1);

    // Add items to expanded set
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      pathToExpand.forEach((item) => newSet.add(item.laui));
      return newSet;
    });

    // Load children for any items in path that haven't been loaded yet
    // Skip monitor folders as they're virtual and use LogsExplorer
    for (const item of pathToExpand) {
      const isMonitorFolder =
        item.item_type === 'folder.monitor' || item.laui?.startsWith('monitor-');
      if (isMonitorFolder) {
        setLoadedChildren((prev) => new Set(prev).add(item.laui));
      } else {
        await loadChildren(item.laui, item.permission);
      }
    }
  };

  // Collapse all folders except those in the path to selected item
  const collapseFoldersExceptPath = async (targetItemId: string | null) => {
    if (!targetItemId) {
      setExpandedItems(new Set());
      return;
    }

    const path = findPath(targetItemId);
    if (path.length === 0) return;

    // Keep only items in the path expanded (but exclude the last one)
    const itemsToKeepExpanded = path.slice(0, -1).map((item) => item.laui);

    // Load children for items in path that haven't been loaded yet
    // Skip monitor folders as they're virtual and use LogsExplorer
    for (const item of path.slice(0, -1)) {
      const isMonitorFolder =
        item.item_type === 'folder.monitor' || item.laui?.startsWith('monitor-');
      if (!isMonitorFolder && !loadedChildren.has(item.laui)) {
        await loadChildren(item.laui, item.permission);
      } else if (isMonitorFolder) {
        // Mark monitor folder as loaded to prevent future load attempts
        setLoadedChildren((prev) => new Set(prev).add(item.laui));
      }
    }

    setExpandedItems(new Set(itemsToKeepExpanded));
  };

  // Load children for a specific supported type under a node (with optional pagination)
  const loadChildrenByType = async (
    itemId: string,
    itemType: string,
    itemPermission: string,
    page: number = 1,
    perPage: number = 25,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc',
    filterState?: string,
    parentItemOverride?: CatalogItem,
  ) => {
    try {
      setLoadingChildren((prev) => new Set(prev).add(itemId));
      const { items: typedChildren, pagination } = await getChildCatalogNodesByType(
        itemId,
        itemType,
        itemPermission,
        isMarketplaceCatalog,
        page,
        perPage,
        sortBy,
        sortOrder,
        filterState,
      );
      const allItems = deduplicateItemsByLaui(extractItems(typedChildren));
      const parentItem = parentItemOverride ?? findItem(itemId);
      const paginationWithPrev = pagination
        ? { ...pagination, has_previous: pagination.current_page > 1 }
        : null;

      setFilteredItemsByType(allItems);
      setFilteredItemsPagination(paginationWithPrev);
      setActiveFilterType(itemType);
      setFilteredFromItem(parentItem);
      setLastFilterType(itemType);
      setLastFilteredFromItem(parentItem);
      setLastFilteredItems(allItems);
      setSelectedItem(null);
      setIsItemFromTable(false);

      if (parentItem) {
        setOpenedFolder(parentItem);
      }
    } catch (e: unknown) {
      console.error('[loadChildrenByType] error:', e);
      const message = e instanceof Error ? e.message : 'Failed to load items for type';
      setError(message);
    } finally {
      setLoadingChildren((prev) => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });
    }
  };

  return {
    loadChildren,
    loadMoreChildren,
    expandPathToItem,
    collapseFoldersExceptPath,
    loadChildrenByType,
  };
}
