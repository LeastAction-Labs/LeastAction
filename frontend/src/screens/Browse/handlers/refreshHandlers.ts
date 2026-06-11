/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useActionContext } from '@/contexts/ActionContext';
import { useNotification } from '@/contexts/NotificationContext';

import { useCatalog } from '../../../contexts/CatalogContext';
import { useCatalogActions, useCatalogTree } from '../hooks';
import { getAttachedActions } from '../utils';

/**
 * Create handlers for FolderSidebar interactions
 *
 * FLOW: FolderSidebar -> ItemDetails / BottomPanel
 *
 * When user interacts with FolderSidebar:
 * 1. handleSelectItem: User clicks an item in the tree
 *    - If folder: Sets as selectedItem AND openedFolder (triggers BottomPanel to show)
 *    - If non-folder: Sets as selectedItem, clears openedFolder (shows ItemDetails)
 *    - Always clears filter state (no active filters from sidebar selection)
 *
 * 2. handleToggleExpand: User expands/collapses a folder
 *    - Expanding: Loads children if needed, sets as openedFolder if it's a folder
 *    - Collapsing: Clears openedFolder if it was the collapsed folder
 */
export function useRefreshHandlers() {
  const { findItem, findPath } = useCatalogTree();
  const { catalogState } = useCatalog();
  const { loadChildren } = useCatalogActions(findItem, findPath);
  const { showSuccess } = useNotification();
  const { setAttachedActions } = useActionContext();

  const handleRefreshItem = async (
    itemId: string,
    itemPermission: string,
    hardRefresh: boolean = false,
  ) => {
    try {
      // Clear the item from loadedChildren to force a refresh
      catalogState.setLoadedChildren((prev) => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });

      // Also clear loadingChildren to be safe
      catalogState.setLoadingChildren((prev) => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });

      // Reload the children
      await loadChildren(itemId, itemPermission);

      if (
        !catalogState.filteredFromItem ||
        !catalogState.filteredFromItem.item_type?.includes('folder')
      ) {
        setAttachedActions({ uiActions: [], taskControlActions: [] });
      } else {
        try {
          const attachedActions = await getAttachedActions(catalogState.filteredFromItem);
          setAttachedActions(attachedActions);
        } catch (error) {
          console.error('Error loading workflow actions:', error);
          setAttachedActions({ uiActions: [], taskControlActions: [] });
        }
      }
      if (hardRefresh) showSuccess(`Refreshed ${itemId} successfully!`);
    } catch {
      /* ignore */
    }
  };

  return {
    handleRefreshItem,
  };
}
