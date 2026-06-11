/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCatalog } from '../../../contexts/CatalogContext';
import { useCatalogActions, useCatalogTree } from '../hooks';
import { useEditorHandlers } from './editorHandlers';
import { useNavigationHandlers } from './navigationHandlers';

/**
 * Create handlers for Breadcrumb interactions
 */
export function useBreadcrumbHandlers() {
  const { catalogState } = useCatalog();
  const { findItem, findPath } = useCatalogTree();
  const { expandPathToItem, collapseFoldersExceptPath, loadChildrenByType } = useCatalogActions(
    findItem,
    findPath,
  );
  const { navigateToPath } = useNavigationHandlers();

  const {
    setActiveFilterType,
    setFilteredFromItem,
    setFilteredItemsByType,
    setSelectedItem,
    setIsItemFromTable,
    setOpenedFolder,
    lastFilteredFromItem,
    lastFilteredItems,
    setLastFilterType,
    setLastFilteredFromItem,
    setLastFilteredItems,
    setIsBreadcrumbLocked,
  } = catalogState;

  const { handleEditorReset } = useEditorHandlers();

  // Handle breadcrumb navigation
  const handleBreadcrumbSelect = async (itemId: string) => {
    handleEditorReset();
    setIsBreadcrumbLocked(false);
    if (itemId.startsWith('filter-')) {
      const filterType = itemId.replace('filter-', '');
      if (lastFilteredFromItem) {
        await loadChildrenByType(
          lastFilteredFromItem.laui,
          filterType,
          lastFilteredFromItem.permission ?? 'view',
        );
        await expandPathToItem(lastFilteredFromItem.laui);
        // Do not call onNavigateToPath here: it would update URL to the folder and trigger
        // useDeepLink, which would overwrite state and redirect away from the action list.
      } else {
        setActiveFilterType(filterType);
        setFilteredFromItem(null);
        setFilteredItemsByType(lastFilteredItems);
        setSelectedItem(null);
        setIsItemFromTable(false);
        navigateToPath?.(null);
      }
      return;
    }

    const item = findItem(itemId);
    if (item) {
      // If clicking on a folder, clear filter and show folder, updating the URL
      if (item.item_type?.startsWith('folder')) {
        setSelectedItem(item);
        setOpenedFolder(item);
        setFilteredItemsByType([]);
        setActiveFilterType(null);
        setFilteredFromItem(null);
        setIsItemFromTable(false);
        setLastFilterType(null);
        setLastFilteredFromItem(null);
        setLastFilteredItems([]);
        await collapseFoldersExceptPath(itemId);
        // Update URL so the folder view is shareable and survives refresh.
        // The lastResolvedLaui guard in useDeepLink prevents a reload loop.
        navigateToPath(item);
      } else {
        // If clicking on an item, show that item and update deep-link URL
        setSelectedItem(item);
        setFilteredItemsByType([]);
        setActiveFilterType(null);
        setFilteredFromItem(null);
        setIsItemFromTable(true);
        const folderToExpand = lastFilteredFromItem || item;
        await expandPathToItem(folderToExpand.laui);
        navigateToPath(item);
      }
    }
  };

  return {
    handleBreadcrumbSelect,
  };
}
