/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useMemo } from 'react';

import { useCatalog } from '../../../contexts/CatalogContext';
import { getBreadcrumbItemId } from '../utils/breadcrumbUtils';
import { findItemById, findPathById } from '../utils/catalogTreeUtils';

/**
 * Provides memoized functions for navigating the catalog tree
 */
export function useCatalogTree() {
  const { catalogState } = useCatalog();
  const {
    items,
    selectedItem,
    filteredFromItem,
    activeFilterType,
    isItemFromTable,
    lastFilteredFromItem,
    deepLinkBreadcrumbPath,
    openedFolder,
  } = catalogState;

  // Memoize findItemById function
  const findItem = useMemo(() => {
    return (targetId: string) => findItemById(items, targetId);
  }, [items]);

  // Memoize findPathById function
  const findPath = useMemo(() => {
    return (targetId: string | null) => findPathById(items, targetId);
  }, [items]);

  // Calculate breadcrumb path; use deep-link path when tree path is not yet available (e.g. right after deep link)
  const breadcrumbPath = useMemo(() => {
    const itemIdForPath = getBreadcrumbItemId(
      activeFilterType,
      filteredFromItem,
      isItemFromTable,
      lastFilteredFromItem,
      selectedItem,
    );
    const filterAccountFolder = (path: ReturnType<typeof findPath>) =>
      path.filter((item) => item.item_type !== 'folder.account');

    const fromTree = findPath(itemIdForPath);
    if (fromTree.length > 0) return filterAccountFolder(fromTree);

    // Non-folder items are not in the sidebar tree; fall back to the opened folder's path
    if (openedFolder && selectedItem && !selectedItem.item_type?.startsWith('folder')) {
      const fromOpenedFolder = findPath(openedFolder.laui);
      if (fromOpenedFolder.length > 0) return filterAccountFolder(fromOpenedFolder);
    }

    if (deepLinkBreadcrumbPath.length > 0) return filterAccountFolder(deepLinkBreadcrumbPath);
    return [];
  }, [
    items,
    selectedItem,
    filteredFromItem,
    activeFilterType,
    isItemFromTable,
    lastFilteredFromItem,
    deepLinkBreadcrumbPath,
    openedFolder,
    findPath,
  ]);

  return {
    findItem,
    findPath,
    breadcrumbPath,
  };
}
