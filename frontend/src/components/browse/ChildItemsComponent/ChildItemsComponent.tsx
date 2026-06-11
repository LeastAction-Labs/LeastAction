/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useState } from 'react';

import { Box, CircularProgress, Typography } from '@mui/material';

import TypeTabs from '@/components/ui/TypeTabs';
import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import type { ProcessedType } from '@/screens/Browse/utils/supportedItemTypesUtils';
import { processSupportedTypes } from '@/screens/Browse/utils/supportedItemTypesUtils';
import {
  getCatalogItemById,
  getChildCatalogNodes,
  getChildCatalogNodesByType,
} from '@/services/catalog.service';

import ItemsTable from '../ItemDetails/ItemsTable';
import type { CatalogNode } from '../types';

export default function ChildItemsComponent() {
  const { catalogType } = useGlobal();
  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;
  const { catalogState, editorState } = useCatalog();
  const { viewingItem } = editorState;
  const item = catalogState.selectedItem || viewingItem || catalogState.openedFolder;
  // Use string primitives as effect deps to avoid re-fetch loops when loadChildrenByType
  // clears selectedItem and re-sets openedFolder (same laui, new object reference).
  const itemLaui = item?.laui ?? '';
  const itemPermission = item?.permission ?? 'view';
  const {
    setActiveFilterType,
    setFilteredItemsByType,
    filteredItemsByType,
    error,
    setError,
    setIsBreadcrumbLocked,
    setFilteredFromItem,
    setFilteredItemsPagination,
  } = catalogState;

  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [processedTypes, setProcessedTypes] = useState<ProcessedType[]>([]);
  const [loadingItem, setLoadingItem] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);

  // Fetch the item to get its supported_types
  useEffect(() => {
    setIsBreadcrumbLocked(true);
    if (!itemLaui) {
      setProcessedTypes([]);
      setSelectedType(null);
      return;
    }

    const fetchItem = async () => {
      setLoadingItem(true);
      try {
        const fetchedItem = await getCatalogItemById(itemLaui, isMarketplaceCatalog);
        const types = fetchedItem.supported_types || [];
        const processed = processSupportedTypes(types);
        setProcessedTypes(processed);

        // Auto-select first type if available and no type is currently selected
        if (processed.length > 0) {
          setSelectedType(processed[0].display);
        } else {
          setSelectedType(null);
        }
      } catch (e: unknown) {
        console.error('Failed to load item for supported_types:', e);
        setProcessedTypes([]);
        setSelectedType(null);
      } finally {
        setLoadingItem(false);
      }
    };

    void fetchItem();
    // itemLaui (string) prevents re-fetch when loadChildrenByType swaps object refs for same item
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemLaui, isMarketplaceCatalog]);

  // Fetch children when itemLaui, selectedType, or itemPermission changes
  useEffect(() => {
    if (!itemLaui) {
      setFilteredItemsByType([]);
      return;
    }

    const fetchChildren = async () => {
      setLoadingItems(true);
      setError('');

      try {
        const permission = itemPermission;
        let childNodes: CatalogNode[];
        let pagination: any = null;

        if (selectedType && processedTypes.length > 0) {
          const typeObj = processedTypes.find((t) => t.display === selectedType);
          if (typeObj) {
            if (typeObj.isFolderGroup) {
              const res = await getChildCatalogNodes(
                itemLaui,
                permission,
                isMarketplaceCatalog,
                1,
                25,
                'folder',
              );
              childNodes = res.items;
              pagination = res.pagination;
            } else {
              const res = await getChildCatalogNodesByType(
                itemLaui,
                typeObj.actualType,
                permission,
                isMarketplaceCatalog,
                1,
                25,
              );
              childNodes = res.items;
              pagination = res.pagination;
            }
          } else {
            const res = await getChildCatalogNodes(
              itemLaui,
              permission,
              isMarketplaceCatalog,
              1,
              25,
              'folder',
            );
            childNodes = res.items;
            pagination = res.pagination;
          }
        } else {
          const res = await getChildCatalogNodes(
            itemLaui,
            permission,
            isMarketplaceCatalog,
            1,
            25,
            'folder',
          );
          childNodes = res.items;
          pagination = res.pagination;
        }

        const childItems = childNodes.map((node) => node.item);

        // Set parent item and pagination so ItemsTable can use server-side pagination
        const currentItem = catalogState.selectedItem || viewingItem || catalogState.openedFolder;
        if (currentItem) setFilteredFromItem(currentItem);
        const paginationWithPrev = pagination
          ? { ...pagination, has_previous: pagination.current_page > 1 }
          : null;
        setFilteredItemsPagination(paginationWithPrev);

        if (selectedType && processedTypes.length > 0) {
          const typeObj = processedTypes.find((t) => t.display === selectedType);
          setActiveFilterType(typeObj?.actualType ?? null);
          if (typeObj && typeObj.isFolderGroup) {
            const folders = childItems.filter((i) =>
              i.item_type?.toLowerCase().startsWith('folder'),
            );
            setFilteredItemsByType(folders);
          } else {
            setFilteredItemsByType(childItems);
          }
        } else {
          setFilteredItemsByType(childItems);
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : 'Failed to load child items';
        setError(message);
        setFilteredItemsByType([]);
      } finally {
        setLoadingItems(false);
      }
    };

    void fetchChildren();
    // itemLaui/itemPermission strings prevent re-fetch loops from pagination side-effects
    // (loadChildrenByType clears selectedItem + re-sets openedFolder to same laui)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemLaui, selectedType, itemPermission, processedTypes.length]);

  const handleTypeClick = useCallback((typeObj: ProcessedType) => {
    setSelectedType(typeObj.display);
  }, []);

  if (loadingItem) {
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

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {processedTypes.length > 0 && (
        <Box sx={{ px: 2, pt: 2, pb: 1 }}>
          <TypeTabs
            types={processedTypes}
            selectedType={selectedType}
            onTypeClick={handleTypeClick}
            folderId={itemLaui}
          />
        </Box>
      )}

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {filteredItemsByType.length === 0 ? (
          <Box
            sx={{
              textAlign: 'center',
              color: 'var(--text-secondary)',
              py: 4,
            }}
          >
            <Typography sx={{ fontSize: FONT_SIZES.SM }}>
              {selectedType ? `No ${selectedType} items found` : 'No child items found'}
            </Typography>
          </Box>
        ) : (
          <ItemsTable />
        )}
      </Box>
    </Box>
  );
}
