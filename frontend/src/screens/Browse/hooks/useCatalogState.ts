/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import type { CatalogItem, CatalogNode, Pagination } from '../../../components/browse/types';

/**
 * Manages the state for the catalog browser
 */
export function useCatalogState() {
  const [items, setItems] = useState<CatalogNode[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [schemaError, setSchemaError] = useState<string>('');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [selectedItem, setSelectedItem] = useState<CatalogItem | null>(null);
  const [loadedChildren, setLoadedChildren] = useState<Set<string>>(new Set());
  const [loadingChildren, setLoadingChildren] = useState<Set<string>>(new Set());
  const [filteredItemsByType, setFilteredItemsByType] = useState<CatalogItem[]>([]);
  const [filteredItemsPagination, setFilteredItemsPagination] = useState<Pagination | null>(null);
  const [activeFilterType, setActiveFilterType] = useState<string | null>(null);
  const [filteredFromItem, setFilteredFromItem] = useState<CatalogItem | null>(null);
  const [openedFolder, setOpenedFolder] = useState<CatalogItem | null>(null);
  const [isItemFromTable, setIsItemFromTable] = useState<boolean>(false);
  const [lastFilterType, setLastFilterType] = useState<string | null>(null);
  const [lastFilteredFromItem, setLastFilteredFromItem] = useState<CatalogItem | null>(null);
  const [lastFilteredItems, setLastFilteredItems] = useState<CatalogItem[]>([]);
  const [selectedSupportedTypeFolder, setSelectedSupportedTypeFolder] = useState<string | null>(
    null,
  );
  /** Path from root to current context (folder or filter parent); used when tree path is not yet available (e.g. deep link). */
  const [deepLinkBreadcrumbPath, setDeepLinkBreadcrumbPath] = useState<CatalogItem[]>([]);
  const [isBreadcrumbLocked, setIsBreadcrumbLocked] = useState<boolean>(false);
  const [childrenPagination, setChildrenPagination] = useState<Record<string, Pagination>>({});
  const [itemNotFound, setItemNotFound] = useState<boolean>(false);
  const [activeWorkflowTab, setActiveWorkflowTab] = useState<number>(0);

  return {
    items,
    setItems,
    isLoading,
    setIsLoading,
    error,
    setError,
    schemaError,
    setSchemaError,
    expandedItems,
    setExpandedItems,
    selectedItem,
    setSelectedItem,
    loadedChildren,
    setLoadedChildren,
    loadingChildren,
    setLoadingChildren,
    filteredItemsByType,
    setFilteredItemsByType,
    filteredItemsPagination,
    setFilteredItemsPagination,
    activeFilterType,
    setActiveFilterType,
    filteredFromItem,
    setFilteredFromItem,
    openedFolder,
    setOpenedFolder,
    isItemFromTable,
    setIsItemFromTable,
    lastFilterType,
    setLastFilterType,
    lastFilteredFromItem,
    setLastFilteredFromItem,
    lastFilteredItems,
    setLastFilteredItems,
    selectedSupportedTypeFolder,
    setSelectedSupportedTypeFolder,
    deepLinkBreadcrumbPath,
    setDeepLinkBreadcrumbPath,
    isBreadcrumbLocked,
    setIsBreadcrumbLocked,
    childrenPagination,
    setChildrenPagination,
    itemNotFound,
    setItemNotFound,
    activeWorkflowTab,
    setActiveWorkflowTab,
  };
}

export type CatalogStateType = ReturnType<typeof useCatalogState>;
