/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useGlobal } from '@/contexts/GlobalContext';
import { getBreadcrumbs } from '@/services/catalog.service';
import { getDocsTree, isDocItem } from '@/utils/docsTree';

import type { CatalogItem, CatalogNode } from '../../../components/browse/types';
import { CatalogMode, useCatalog } from '../../../contexts/CatalogContext';
import { useCatalogActions, useCatalogTree } from '../hooks';
import { flattenBreadcrumbChain } from '../utils';
import { useEditorHandlers } from './editorHandlers';
import { useNavigationHandlers } from './navigationHandlers';

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
export function useSidebarHandlers() {
  const { findItem, findPath } = useCatalogTree();

  const { loadChildren, loadMoreChildren, expandPathToItem, loadChildrenByType } =
    useCatalogActions(findItem, findPath);

  const { currentProjectLaui, setCurrentProjectLaui } = useGlobal();
  const { catalogState, editorState, setMode } = useCatalog();

  const { handleEditorReset, handleViewItem } = useEditorHandlers();

  const { navigateToPath } = useNavigationHandlers();

  const onFormReset = () => {
    handleEditorReset();
    setMode(CatalogMode.DEFAULT);
  };

  const {
    expandedItems,
    setExpandedItems,
    setSelectedItem,
    setFilteredItemsByType,
    setActiveFilterType,
    setFilteredFromItem,
    setIsItemFromTable,
    setLastFilterType,
    setLastFilteredFromItem,
    setLastFilteredItems,
    setOpenedFolder,
    openedFolder,
    loadedChildren,
    setLoadedChildren,
    setIsBreadcrumbLocked,
    setActiveWorkflowTab,
    setDeepLinkBreadcrumbPath,
  } = catalogState;

  /**
   * Handle item selection from FolderSidebar
   *
   * CASE 1: Folder selected
   *   - selectedItem = folder
   *   - openedFolder = folder (triggers BottomPanel)
   *   - ItemDetails shows FolderView
   *   - BottomPanel shows folder's supported types
   *
   * CASE 2: Non-folder selected
   *   - selectedItem = item
   *   - openedFolder = null (hides BottomPanel)
   *   - ItemDetails shows ItemView
   */
  const handleSelectItem = async (itemIdOrItem: string | CatalogItem) => {
    const itemId = typeof itemIdOrItem === 'string' ? itemIdOrItem : itemIdOrItem.laui;

    onFormReset();
    setIsBreadcrumbLocked(false);
    // Special handling for virtual "Shared With Me" node
    if (itemId === 'shared') {
      const sharedVirtualItem: CatalogItem = {
        laui: 'shared',
        name: 'Shared With Me',
        item_type: '',
        permission: 'view',
      };

      // Clear all filter state - sidebar selection is always a "clean" selection
      setSelectedItem(sharedVirtualItem);
      setFilteredItemsByType([]);
      setActiveFilterType(null);
      setFilteredFromItem(null);
      setIsItemFromTable(false);
      setLastFilterType(null);
      setLastFilteredFromItem(null);
      setLastFilteredItems([]);

      // Virtual node should open BottomPanel
      setOpenedFolder(sharedVirtualItem);
      // Skip URL update for virtual nodes (no deep link for "shared")
      return;
    }

    // Doc items are in-memory only and not in the catalog tree
    if (isDocItem(itemId)) {
      const tree = getDocsTree();
      const findDocNode = (node: any): any => {
        if (node.item.laui === itemId) return node.item;
        for (const c of node.children) {
          const f = findDocNode(c);
          if (f) return f;
        }
        return null;
      };
      const docItem = findDocNode(tree);
      if (docItem) await handleViewItem(docItem);
      return;
    }

    const item = typeof itemIdOrItem === 'object' ? itemIdOrItem : findItem(itemId);
    if (!item) return;

    // Re-clicking the same folder should not wipe filter/task state
    const isWorkflowFolder = item.item_type?.toLowerCase() === 'folder.workflow';
    console.log(
      '[handleSelectItem] itemId:',
      itemId,
      'selectedItem:',
      catalogState.selectedItem?.laui,
      'isWorkflowFolder:',
      isWorkflowFolder,
      'activeFilterType:',
      catalogState.activeFilterType,
    );
    if (
      (catalogState.selectedItem?.laui === itemId || openedFolder?.laui === itemId) &&
      item.item_type?.toLowerCase().startsWith('folder')
    ) {
      console.log('[handleSelectItem] EARLY RETURN for same folder');
      setOpenedFolder(item);
      navigateToPath(item);
      if (isWorkflowFolder) {
        setActiveWorkflowTab(0);
      }
      return;
    }

    // Clear all filter state - sidebar selection is always a "clean" selection
    setSelectedItem(item);
    setFilteredItemsByType([]);
    setActiveFilterType(null);
    setFilteredFromItem(null);
    setIsItemFromTable(false);
    setLastFilterType(null);
    setLastFilteredFromItem(null);
    setLastFilteredItems([]);

    // Determine if this is a folder to control BottomPanel visibility
    const isFolder = item.item_type?.toLowerCase().startsWith('folder');
    // Virtual nodes (like "Shared With Me") with empty item_type should also behave like folders
    const isVirtualNode = item.item_type === '';

    if (isFolder || isVirtualNode) {
      // Folder/Virtual node selected: Show in ItemDetails AND open BottomPanel
      setOpenedFolder(item);
      // Reset workflow tab when selecting a folder
      if (item.item_type === 'folder.workflow') {
        setActiveWorkflowTab(0);
      }
      if (!isVirtualNode) {
        navigateToPath(item);
      }
    } else {
      // Non-folder selected: keep parent folder context so breadcrumb shows "action" and is clickable
      const path = findPath(itemId);
      const parentFolder = path.length >= 2 ? path[path.length - 2] : null;
      if (parentFolder) {
        setOpenedFolder(parentFolder);
        setLastFilteredFromItem(parentFolder);
        setLastFilterType(item.item_type ?? null);
      } else {
        setOpenedFolder(null);
      }
      await handleViewItem(item);
    }

    // Expand path in sidebar. If item came from FolderView table (not tree), resolve
    // ancestors via API — the item may not be in the sidebar tree yet (parent's children
    // may not have been loaded, or were loaded with a page limit that didn't include it).
    if (typeof itemIdOrItem === 'object') {
      try {
        const breadcrumbData = await getBreadcrumbs(itemId);
        if (breadcrumbData?.items?.length) {
          const chain = flattenBreadcrumbChain(breadcrumbData.items);
          const knownPath = chain.map((n: CatalogNode) => n.item);
          setDeepLinkBreadcrumbPath(knownPath);

          // Expand all ancestors in sidebar
          setExpandedItems((prev) => {
            const next = new Set(prev);
            knownPath.forEach((a) => next.add(a.laui));
            return next;
          });

          // Force-reload the clicked folder's parent so the folder appears in the sidebar
          // tree (it may have been skipped due to pagination or loadedChildren cache).
          // Also reload the clicked folder's own children so it can be expanded.
          // Use permission from the live tree item (has correct value) or fall back to 'view'.
          const clickedFolderNode = knownPath[knownPath.length - 1];
          const parentOfClicked = knownPath.length >= 2 ? knownPath[knownPath.length - 2] : null;
          if (parentOfClicked) {
            const treeParent = findItem(parentOfClicked.laui);
            const parentPerm = treeParent?.permission ?? parentOfClicked.permission ?? 'view';
            await loadChildren(parentOfClicked.laui, parentPerm, true);
          }
          if (clickedFolderNode) {
            const treeNode = findItem(clickedFolderNode.laui);
            const nodePerm = treeNode?.permission ?? clickedFolderNode.permission ?? 'view';
            await loadChildren(clickedFolderNode.laui, nodePerm, true);
          }
        }
      } catch {
        // Non-fatal: sidebar just won't auto-expand
      }
    } else {
      await expandPathToItem(itemId);
    }
    //onNavigateToPath?.(item);
  };

  const enhancedHandleSelectItem = async (itemIdOrItem: string | CatalogItem) => {
    const item = typeof itemIdOrItem === 'object' ? itemIdOrItem : findItem(itemIdOrItem);
    if (item) {
      const projectLaui =
        item.item_type === 'folder.project' ? item.laui : (item.project_laui ?? null);
      if (projectLaui && projectLaui !== currentProjectLaui) {
        setCurrentProjectLaui(projectLaui);
      }
    }
    await handleSelectItem(itemIdOrItem);
  };

  /**
   * Handle expand/collapse toggle in FolderSidebar
   *
   * CASE 1: Expanding a folder
   *   - Loads children if not already loaded (except for monitor folders)
   *   - If folder type: Sets as openedFolder (triggers BottomPanel)
   *   - Also selects the folder (for consistency)
   *
   * CASE 2: Collapsing a folder
   *   - If it was the openedFolder: Clears openedFolder (hides BottomPanel)
   *   - Otherwise: Just collapses (no state change)
   */
  const handleToggleExpand = async (itemId: string, itemPermission: string) => {
    const isCurrentlyExpanded = expandedItems.has(itemId);

    // Special handling for virtual "Shared With Me" node
    let item: CatalogItem | null = null;
    if (itemId === 'shared') {
      item = {
        laui: 'shared',
        name: 'Shared With Me',
        item_type: '',
        permission: 'view',
      };
    } else {
      item = findItem(itemId);
    }

    // Check if this is a monitor folder (virtual folder for logs)
    const isMonitorFolder = item?.item_type === 'folder.monitor' || itemId.startsWith('monitor-');

    // Toggle expanded state
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (isCurrentlyExpanded) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });

    if (!isCurrentlyExpanded) {
      // EXPANDING: Load children and update state
      if (item) {
        const isFolder = item.item_type?.toLowerCase().startsWith('folder');
        // Special handling for virtual nodes like "Shared With Me" (empty item_type)
        const isVirtualNode = item.item_type === '';
        const isWorkflowFolderExpand = item.item_type?.toLowerCase() === 'folder.workflow';

        if (isFolder || isVirtualNode) {
          // Folder/Virtual node expanded: Set as openedFolder and select it
          // This ensures BottomPanel shows the folder's contents
          // Skip this for monitor folders as they show LogsExplorer instead
          setOpenedFolder(item);
          setSelectedItem(item);

          // Clear filter state for clean folder view.
          // Skip clearing when:
          // - workflow folder already selected (task state managed by FolderView)
          // - this folder is already openedFolder (re-click while viewing its children)
          const isAlreadyOpenedFolder = openedFolder?.laui === itemId;
          console.log(
            '[handleToggleExpand] EXPANDING, isWorkflowFolderExpand:',
            isWorkflowFolderExpand,
            'isAlreadySelected:',
            catalogState.selectedItem?.laui === itemId,
            'isAlreadyOpenedFolder:',
            isAlreadyOpenedFolder,
          );
          if (
            !(isWorkflowFolderExpand && catalogState.selectedItem?.laui === itemId) &&
            !isAlreadyOpenedFolder
          ) {
            setFilteredItemsByType([]);
            setActiveFilterType(null);
            setFilteredFromItem(null);
            setIsItemFromTable(false);
            setLastFilterType(null);
            setLastFilteredFromItem(null);
            setLastFilteredItems([]);
          }

          if (!isVirtualNode) {
            navigateToPath(item);
          }
        }
      }

      // Load children if not already loaded
      // Skip loading for virtual nodes (like "Shared With Me") as their children are pre-loaded
      const isVirtualNode = item?.item_type === '';
      if (!isMonitorFolder && !loadedChildren.has(itemId) && !isVirtualNode) {
        await loadChildren(itemId, itemPermission);
      } else if (isVirtualNode) {
        // Mark virtual nodes as loaded since their children are already in the tree
        setLoadedChildren((prev) => new Set(prev).add(itemId));
      } else if (isMonitorFolder) {
        // Mark monitor folder as loaded to prevent future load attempts
        // Monitor folders use LogsExplorer which handles its own data loading
        setLoadedChildren((prev) => new Set(prev).add(itemId));
      }
    } else {
      // COLLAPSING: Clear openedFolder if it was the collapsed folder, but only if it's not selected.
      // Exception: if the user is actively viewing children of this folder (filteredFromItem matches),
      // keep openedFolder so the table stays visible when re-clicking an already-open folder.
      const isViewingChildren = catalogState.filteredFromItem?.laui === itemId;
      if (
        item &&
        openedFolder?.laui === itemId &&
        catalogState.selectedItem?.laui !== itemId &&
        !isViewingChildren
      ) {
        setOpenedFolder(null);
      }
    }
  };

  const handleSelectSupportedType = async (
    itemId: string,
    itemType: string,
    itemPermission: string,
  ) => {
    onFormReset();
    await loadChildrenByType(itemId, itemType, itemPermission);
    const item = findItem(itemId);
    if (item) navigateToPath(item, itemType);
  };

  const enhancedHandleToggleExpand = async (itemId: string, itemPermission: string) => {
    // Skip API calls for documentation items
    if (isDocItem(itemId)) {
      // Just toggle the expand catalogState without loading children
      catalogState.setExpandedItems((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(itemId)) {
          newSet.delete(itemId);
        } else {
          newSet.add(itemId);
        }
        return newSet;
      });
      return;
    }

    await handleToggleExpand(itemId, itemPermission);
  };

  const handleSelectUsers = () => {
    setMode(CatalogMode.USERS);
    catalogState.setSelectedItem(null);
    catalogState.setOpenedFolder(null);
    catalogState.setActiveFilterType(null);
    catalogState.setFilteredItemsByType([]);
    handleEditorReset();
  };

  const handleSelectGroups = () => {
    setMode(CatalogMode.GROUPS);
    catalogState.setSelectedItem(null);
    catalogState.setOpenedFolder(null);
    catalogState.setActiveFilterType(null);
    catalogState.setFilteredItemsByType([]);
    editorState.setFormMode(null);
    editorState.setCreateFilterType(null);
    editorState.setEditingItem(null);
    editorState.setViewingItem(null);
    editorState.setFormSchema(null);
  };

  return {
    handleSelectItem: enhancedHandleSelectItem,
    handleToggleExpand: enhancedHandleToggleExpand,
    handleSelectSupportedType,
    handleSelectGroups,
    handleSelectUsers,
    loadMoreChildren,
  };
}
