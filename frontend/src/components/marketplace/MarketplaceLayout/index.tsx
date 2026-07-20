/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Box } from '@mui/material';

import { LeftSidebar, TopHeader } from '@/components/browse';
import ItemTabBar from '@/components/browse/ItemTabBar/ItemTabBar';
import ImportModal from '@/components/browse/modals/ImportModal';
import type { CatalogItem, FullItemData } from '@/components/browse/types';
import { CORE_BACKEND_URL } from '@/config/urls';
import { setCoreVersion } from '@/config/version';
import { useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { httpJson } from '@/services/api';
import { getCatalogItemById, searchCatalogItems } from '@/services/catalog.service';
import { parseMarketplaceQuery } from '@/utils/marketplaceSearch';

import MarketplaceBrowse from '../MarketplaceBrowse/MarketplaceBrowse';
import type { MarketplaceFacets } from '../MarketplaceBrowse/MarketplaceFilterSidebar';
import MarketplaceItemDetail from '../MarketplaceItemDetail/MarketplaceItemDetail';
import MarketplaceSearchPanel from '../MarketplaceSearchPanel/MarketplaceSearchPanel';

const PANEL_MIN = 200;
const PANEL_MAX = 600;
const PANEL_DEFAULT = 320;

const TOP_TYPES_LIMIT = Infinity;
const TOP_CATEGORIES_LIMIT = 10;
const TOP_TAGS_LIMIT = 20;

const FACET_PROJECTION = ['item_type', 'category', 'tags'];
const FACET_PAGE_SIZE = 1000;

interface MarketplaceLayoutProps {
  initialQuery?: string;
  initialLaui?: string;
  onSearchChange?: (q: string) => void;
  onItemSelect?: (laui: string) => void;
  onBack?: () => void;
}

export default function MarketplaceLayout({
  initialQuery = '',
  initialLaui,
  onSearchChange,
  onItemSelect,
  onBack,
}: MarketplaceLayoutProps) {
  const { showError } = useNotification();
  const { addTab } = useGlobal();

  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [searchResults, setSearchResults] = useState<CatalogItem[]>([]);
  const [facetSourceItems, setFacetSourceItems] = useState<CatalogItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<FullItemData | null>(null);
  const [selectedLaui, setSelectedLaui] = useState<string | null>(initialLaui ?? null);
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [panelWidth, setPanelWidth] = useState(PANEL_DEFAULT);
  const pageRef = useRef(1);
  const lastFiltersRef = useRef<Record<string, string | string[]>>({});
  const isResizingRef = useRef(false);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(PANEL_DEFAULT);

  const parsedQuery = useMemo(() => parseMarketplaceQuery(searchQuery), [searchQuery]);

  const facets: MarketplaceFacets = useMemo(() => {
    const typeCounts = new Map<string, number>();
    const categoryCounts = new Map<string, number>();
    const tagCounts = new Map<string, number>();
    const bump = (map: Map<string, number>, key: string) => map.set(key, (map.get(key) ?? 0) + 1);
    for (const item of facetSourceItems) {
      if (item.item_type) bump(typeCounts, item.item_type);
      if (item.category) bump(categoryCounts, item.category);
      for (const tag of item.tags ?? []) bump(tagCounts, tag);
    }
    const topByCount = (map: Map<string, number>, limit: number) =>
      [...map.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, limit)
        .map(([key]) => key);
    return {
      types: topByCount(typeCounts, TOP_TYPES_LIMIT),
      categories: topByCount(categoryCounts, TOP_CATEGORIES_LIMIT),
      tags: topByCount(tagCounts, TOP_TAGS_LIMIT),
    };
  }, [facetSourceItems]);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasAutoSelected = useRef(false);

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    isResizingRef.current = true;
    resizeStartXRef.current = e.clientX;
    resizeStartWidthRef.current = panelWidth;
    const onMove = (ev: MouseEvent) => {
      if (!isResizingRef.current) return;
      const next = Math.min(
        PANEL_MAX,
        Math.max(PANEL_MIN, resizeStartWidthRef.current + ev.clientX - resizeStartXRef.current),
      );
      setPanelWidth(next);
    };
    const onUp = () => {
      isResizingRef.current = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  };

  const fetchDetail = useCallback(
    async (laui: string) => {
      setIsDetailLoading(true);
      try {
        const data = await getCatalogItemById(laui, true);
        setSelectedItem(data);
      } catch {
        /* ignore */
      } finally {
        setIsDetailLoading(false);
      }
    },
    [showError],
  );

  const PROJECTION = [
    'name',
    'item_type',
    'description',
    'version_compatibility',
    'version_details',
    'image_url',
    'tags',
    'category',
    'publisher',
    'verified',
  ];

  const buildFilters = (query: string): Record<string, string | string[]> => {
    const { nameQuery, fieldFilters } = parseMarketplaceQuery(query);
    const filters: Record<string, string | string[]> = {};
    if (nameQuery.trim()) filters.name = nameQuery.trim();
    for (const [field, values] of Object.entries(fieldFilters)) {
      filters[field] = values;
    }
    return filters;
  };

  const runSearch = useCallback(
    async (query: string, autoSelectLaui?: string) => {
      setIsSearchLoading(true);
      pageRef.current = 1;
      try {
        const filters = buildFilters(query);
        lastFiltersRef.current = filters;
        const data = await searchCatalogItems(undefined, true, {
          filters: Object.keys(filters).length ? filters : undefined,
          perPage: 100,
          page: 1,
          projection: PROJECTION,
        });
        const items: CatalogItem[] = (data?.items ?? []).map((i: any) => i.item ?? i);
        setSearchResults(items);
        setHasNextPage(data?.pagination?.has_next ?? false);

        // On initial load: restore URL-specified item (browse landing page shows no selection by default)
        if (autoSelectLaui && !hasAutoSelected.current) {
          hasAutoSelected.current = true;
          setSelectedLaui(autoSelectLaui);
          await fetchDetail(autoSelectLaui);
        }
      } catch {
        /* ignore */
      } finally {
        setIsSearchLoading(false);
      }
    },
    [fetchDetail, showError],
  );

  const loadMore = useCallback(async () => {
    if (!hasNextPage || isLoadingMore) return;
    setIsLoadingMore(true);
    const nextPage = pageRef.current + 1;
    try {
      const filters = lastFiltersRef.current;
      const data = await searchCatalogItems(undefined, true, {
        filters: Object.keys(filters).length ? filters : undefined,
        perPage: 100,
        page: nextPage,
        projection: PROJECTION,
      });
      const newItems: CatalogItem[] = (data?.items ?? []).map((i: any) => i.item ?? i);
      setSearchResults((prev) => [...prev, ...newItems]);
      setHasNextPage(data?.pagination?.has_next ?? false);
      pageRef.current = nextPage;
    } catch {
      /* ignore */
    } finally {
      setIsLoadingMore(false);
    }
  }, [hasNextPage, isLoadingMore, showError]);

  // Fetches the full set of distinct item_type/category/tags values across the whole
  // marketplace catalog, independent of the current search/filter/pagination state, so the
  // sidebar facets aren't limited to whatever happens to be on the currently loaded page.
  const fetchFacets = useCallback(async () => {
    try {
      const items: CatalogItem[] = [];
      let page = 1;
      let hasNext = true;
      while (hasNext) {
        const data = await searchCatalogItems(undefined, true, {
          perPage: FACET_PAGE_SIZE,
          page,
          projection: FACET_PROJECTION,
        });
        const pageItems: CatalogItem[] = (data?.items ?? []).map((i: any) => i.item ?? i);
        items.push(...pageItems);
        hasNext = data?.pagination?.has_next ?? false;
        page += 1;
      }
      setFacetSourceItems(items);
    } catch {
      /* ignore */
    }
  }, []);

  // Fetch and cache core version from backend on marketplace open
  useEffect(() => {
    httpJson<{ core_version: string }>(`${CORE_BACKEND_URL}/api/v1/system/info`)
      .then((data) => {
        if (data?.core_version) setCoreVersion(data.core_version);
      })
      .catch(() => {});
  }, []);

  // Initial load — restore URL state if present
  useEffect(() => {
    void runSearch(initialQuery, initialLaui);
    void fetchFacets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // React to external laui changes (e.g. tab bar click while already on /marketplace,
  // or navigating back to the bare /marketplace browse landing page)
  useEffect(() => {
    if (initialLaui && initialLaui !== selectedLaui) {
      setSelectedLaui(initialLaui);
      void fetchDetail(initialLaui);
    } else if (!initialLaui && selectedLaui) {
      setSelectedLaui(null);
      setSelectedItem(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialLaui]);

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    onSearchChange?.(query);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSearch(query);
    }, 300);
  };

  const handleAddFilter = (field: string, value: string) => {
    const token = `${field}:"${value}"`;
    if (searchQuery.includes(token)) return;
    handleSearchChange(`${searchQuery} ${token}`.trim());
  };

  const handleSelect = async (item: CatalogItem) => {
    if (item.laui === selectedLaui) return;
    setSelectedLaui(item.laui);
    onItemSelect?.(item.laui);
    addTab({
      laui: item.laui,
      name: item.name ?? '',
      item_type: item.item_type ?? '',
      source: 'marketplace',
    });
    await fetchDetail(item.laui);
  };

  const handleBack = () => {
    setSelectedLaui(null);
    setSelectedItem(null);
    onBack?.();
  };

  return (
    <Box
      sx={{
        bgcolor: 'var(--bg-primary)',
        color: 'var(--text-primary)',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <TopHeader />

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <LeftSidebar />

        {selectedLaui ? (
          /* Marketplace two-panel body — existing detail experience, unchanged */
          <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            <MarketplaceSearchPanel
              searchQuery={searchQuery}
              onSearchChange={handleSearchChange}
              parsedQuery={parsedQuery}
              results={searchResults}
              isLoading={isSearchLoading}
              isLoadingMore={isLoadingMore}
              hasNextPage={hasNextPage}
              onLoadMore={() => void loadMore()}
              selectedLaui={selectedLaui}
              onSelect={(item) => void handleSelect(item)}
              onBack={handleBack}
              width={panelWidth}
            />

            {/* Resize handle */}
            <Box
              onMouseDown={handleResizeMouseDown}
              sx={{
                width: 6,
                flexShrink: 0,
                cursor: 'col-resize',
                bgcolor: 'transparent',
                '&:hover': { bgcolor: 'var(--accent)', opacity: 0.5 },
              }}
            />

            <Box
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
              }}
            >
              <ItemTabBar activeItemLaui={selectedLaui} />
              <MarketplaceItemDetail
                item={selectedItem}
                isLoading={isDetailLoading}
                onAddFilter={handleAddFilter}
              />
            </Box>
          </Box>
        ) : (
          /* Marketplace browse landing page — filters + card grid, no item selected */
          <MarketplaceBrowse
            searchQuery={searchQuery}
            onSearchChange={handleSearchChange}
            parsedQuery={parsedQuery}
            facets={facets}
            onToggleFilter={handleAddFilter}
            results={searchResults}
            isLoading={isSearchLoading}
            isLoadingMore={isLoadingMore}
            hasNextPage={hasNextPage}
            onLoadMore={() => void loadMore()}
            onSelect={(item) => void handleSelect(item)}
          />
        )}
      </Box>

      <ImportModal />
    </Box>
  );
}
