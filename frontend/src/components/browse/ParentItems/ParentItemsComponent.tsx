/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Box, CircularProgress, Typography } from '@mui/material';

import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { getParentCatalogNodesByType } from '@/services/catalog.service';

import ItemsTable from '../ItemDetails/ItemsTable';
import type { CatalogNode } from '../types';

export default function ParentItemsComponent() {
  const { catalogType } = useGlobal();
  const { catalogState, editorState } = useCatalog();
  const { viewingItem } = editorState;
  const {
    filteredItemsByType,
    error,
    setActiveFilterType,
    setFilteredItemsByType,
    setError,
    setIsBreadcrumbLocked,
  } = catalogState;
  const item = catalogState.selectedItem || viewingItem || catalogState.openedFolder;
  const itemLaui = item.laui;
  const itemType = item.item_type;
  const itemPermission = item.permission;

  const [loadingItems, setLoadingItems] = useState(false);

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  useEffect(() => {
    setIsBreadcrumbLocked(true);
    if (!itemLaui) {
      setFilteredItemsByType([]);
      return;
    }

    const fetchParents = async () => {
      setLoadingItems(true);
      setError('');

      try {
        const permission = itemPermission || 'view';

        const res = await getParentCatalogNodesByType(
          itemLaui,
          itemType,
          permission,
          isMarketplaceCatalog,
        );
        const parentNodes: CatalogNode[] = res.items;

        const parentItems = parentNodes.map((node) => node.item);
        setFilteredItemsByType(parentItems);
        setActiveFilterType(itemType);
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : 'Failed to load parent items';
        setError(message);
        setFilteredItemsByType([]);
      } finally {
        setLoadingItems(false);
      }
    };

    void fetchParents();
  }, [itemLaui, itemType, itemPermission]);

  if (loadingItems) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          py: 4,
        }}
      >
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box
        sx={{
          textAlign: 'center',
          color: 'var(--text-secondary)',
          py: 4,
        }}
      >
        <Typography sx={{ fontSize: FONT_SIZES.SM }}>{error}</Typography>
      </Box>
    );
  }

  if (filteredItemsByType.length === 0) {
    return (
      <Box
        sx={{
          textAlign: 'center',
          color: 'var(--text-secondary)',
          py: 4,
        }}
      >
        <Typography sx={{ fontSize: FONT_SIZES.SM }}>No parent items found</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
      <ItemsTable />
    </Box>
  );
}
