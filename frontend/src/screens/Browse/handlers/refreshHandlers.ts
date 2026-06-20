/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useActionContext } from '@/contexts/ActionContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { getRootCatalogNodes } from '@/services/catalog.service';

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
  const { catalogType } = useGlobal();
  const { loadChildren } = useCatalogActions(findItem, findPath);
  const { showSuccess } = useNotification();
  const { setAttachedActions } = useActionContext();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

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

      // Reload the children. Force the fetch: setLoadedChildren above is an
      // async state update, so loadChildren's own loadedChildren closure is
      // still stale here and its cache guard would otherwise skip the refetch.
      await loadChildren(itemId, itemPermission, true);

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

  /**
   * Reload the entire sidebar tree from the root, invalidating the
   * loadedChildren cache. Used after delete/restore, where an item moves
   * between two subtrees (source parent <-> trash) and a single-node refresh
   * cannot keep both consistent. Currently-expanded folders are re-fetched so
   * the user's expansion state is preserved.
   */
  const handleRefreshTree = async () => {
    try {
      const { items: root } = await getRootCatalogNodes(isMarketplaceCatalog);
      catalogState.setItems(root);

      // Invalidate all cached children. The root response already pre-nests the
      // account folder's children, so re-mark it loaded to avoid a redundant
      // refetch that would overwrite them with a paginated subset.
      const accountNode = root[0]?.item?.item_type === 'folder.account' ? root[0].item : null;
      catalogState.setLoadedChildren(accountNode ? new Set([accountNode.laui]) : new Set());

      // Re-fetch children for folders that are currently expanded so the tree
      // keeps its shape. Skip virtual/monitor nodes which load lazily elsewhere.
      const expandedIds = Array.from(catalogState.expandedItems);
      for (const id of expandedIds) {
        if (accountNode && id === accountNode.laui) continue;
        const item = findItem(id);
        if (!item) continue;
        const isVirtualNode = item.item_type === '';
        const isMonitorFolder =
          item.item_type === 'folder.monitor' || item.laui.startsWith('monitor-');
        if (isVirtualNode || isMonitorFolder) continue;
        await loadChildren(id, item.permission ?? 'view', true);
      }
    } catch (error) {
      console.error('Error refreshing sidebar tree:', error);
    }
  };

  return {
    handleRefreshItem,
    handleRefreshTree,
  };
}
