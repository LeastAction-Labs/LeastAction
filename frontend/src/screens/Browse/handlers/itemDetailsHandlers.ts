/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem } from '../../../components/browse/types';
import { useCatalog } from '../../../contexts/CatalogContext';
import { useNavigationHandlers } from './navigationHandlers';

type ItemDetailsHandlersDeps = {
  expandPathToItem: (targetItemId: string | null) => Promise<void>;
  collapseFoldersExceptPath: (targetItemId: string | null) => Promise<void>;
  loadChildren: (itemId: string, itemPermission: string) => Promise<void>;
  onNavigateToPath?: (item: CatalogItem | null) => void;
};

/**
 * Create handlers for ItemDetails interactions
 *
 * FLOW: ItemDetails -> BottomPanel / ItemDetails (recursive)
 *
 * ItemDetails can show:
 * - ItemsView: Filtered list of items (from type chip click)
 * - ItemView: Single item details (from table row click)
 * - FolderView: Folder details (from sidebar selection)
 *
 * When user clicks an item in ItemDetails:
 *
 * 1. Folder clicked (from ItemsView table):
 *    - Navigate to that folder (new openedFolder, new BottomPanel)
 *    - Clear filter state
 *
 * 2. Non-folder clicked (from ItemsView table):
 *    - Show item details (ItemView)
 *    - Keep filter context for breadcrumbs
 */
export function useItemDetailsHandlers({ expandPathToItem }: ItemDetailsHandlersDeps) {
  const { catalogState } = useCatalog();
  const {
    setSelectedItem,
    setFilteredItemsByType,
    setActiveFilterType,
    setFilteredFromItem,
    setIsItemFromTable,
    setLastFilterType,
    setLastFilteredFromItem,
    setLastFilteredItems,
    setOpenedFolder,
  } = catalogState;
  const { navigateToPath } = useNavigationHandlers();

  /**
   * Handle item click from ItemDetails
   *
   * This is called when user clicks a row in ItemsView (filtered list)
   *
   * CASE 1: Folder clicked
   *   - Navigate to the folder (same as BottomPanel folder click)
   *   - New openedFolder = clicked folder
   *   - Clear all filter state
   *   - BottomPanel shows new folder's contents
   *
   * CASE 2: Non-folder clicked
   *   - Show item in ItemView
   *   - Keep filter context (lastFilteredFromItem) for breadcrumbs
   *   - Expand path to filter source folder for context
   */
  const handleItemClick = async (item: CatalogItem) => {
    if (item.item_type?.startsWith('folder')) {
      // Handle folder click - expand and show in sidebar
      setSelectedItem(item);
      setOpenedFolder(item);
      setActiveFilterType(null);
      setFilteredItemsByType([]);
      setFilteredFromItem(null);
      setIsItemFromTable(false);

      await expandPathToItem(item.laui);
      navigateToPath(item);
    } else {
      // Handle item click - show item details but keep folder + type context for breadcrumb "back"
      const folder = catalogState.filteredFromItem;
      const filterType = catalogState.activeFilterType;
      const items = catalogState.filteredItemsByType;
      setSelectedItem(item);
      setOpenedFolder(folder ?? null);
      setActiveFilterType(null);
      setFilteredItemsByType([]);
      setFilteredFromItem(null);
      setIsItemFromTable(true);
      if (folder && filterType) {
        setLastFilteredFromItem(folder);
        setLastFilterType(filterType);
        setLastFilteredItems(items ?? []);
      }
    }
  };

  return {
    handleItemClick,
  };
}
