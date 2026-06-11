/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useNavigate, useSearch } from '@tanstack/react-router';

import { useCatalog } from '@/contexts/CatalogContext';
import { useNotification } from '@/contexts/NotificationContext';

import { useCatalogActions, useCatalogTree } from '../hooks';

export const usePaginationHandlers = () => {
  const { findItem, findPath } = useCatalogTree();
  const { loadChildrenByType } = useCatalogActions(findItem, findPath);
  const { catalogState } = useCatalog();
  const { showSuccess } = useNotification();
  const navigate = useNavigate();
  const urlSearch = useSearch({ strict: false });

  const handleFilteredListPageChange = (
    page: number,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc',
    filterState?: string,
  ) => {
    if (!catalogState.filteredFromItem || !catalogState.activeFilterType) return;
    void navigate({
      to: '.',
      search: (prev: any) => ({
        ...prev,
        page,
        sortBy: sortBy || undefined,
        sortOrder: sortBy ? sortOrder : undefined,
        filterState: filterState || undefined,
      }),
      replace: true,
    });
    void loadChildrenByType(
      catalogState.filteredFromItem.laui,
      catalogState.activeFilterType,
      catalogState.filteredFromItem.permission,
      page,
      catalogState.filteredItemsPagination?.per_page ?? 25,
      sortBy,
      sortOrder,
      filterState,
    );
  };

  const handleFilteredListItemsPerPageChange = (
    perPage: number,
    sortBy?: string,
    sortOrder?: 'asc' | 'desc',
    filterState?: string,
  ) => {
    if (!catalogState.filteredFromItem || !catalogState.activeFilterType) return;
    void navigate({
      to: '.',
      search: (prev: any) => ({
        ...prev,
        page: 1,
        perPage,
        sortBy: sortBy || undefined,
        sortOrder: sortBy ? sortOrder : undefined,
        filterState: filterState || undefined,
      }),
      replace: true,
    });
    void loadChildrenByType(
      catalogState.filteredFromItem.laui,
      catalogState.activeFilterType,
      catalogState.filteredFromItem.permission,
      1,
      perPage,
      sortBy,
      sortOrder,
      filterState,
    );
  };

  const refreshFilteredList = async (
    sortBy?: string,
    sortOrder?: 'asc' | 'desc',
    filterState?: string,
  ) => {
    if (!catalogState.filteredFromItem || !catalogState.activeFilterType) return;
    const currentPage = catalogState.filteredItemsPagination?.current_page ?? 1;
    await loadChildrenByType(
      catalogState.filteredFromItem.laui,
      catalogState.activeFilterType,
      catalogState.filteredFromItem.permission,
      currentPage,
      catalogState.filteredItemsPagination?.per_page ?? 25,
      sortBy,
      sortOrder,
      filterState,
    );
  };

  const handleRefreshFilteredList = async () => {
    try {
      await refreshFilteredList(
        urlSearch.sortBy,
        urlSearch.sortOrder as 'asc' | 'desc' | undefined,
        urlSearch.filterState,
      );
      showSuccess('Task table refreshed successfully!');
    } catch {
      /* ignore */
    }
  };

  return {
    handleFilteredListItemsPerPageChange,
    handleFilteredListPageChange,
    handleRefreshFilteredList,
    refreshFilteredList,
  };
};
