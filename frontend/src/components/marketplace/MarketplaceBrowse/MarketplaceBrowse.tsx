/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useRef } from 'react';

import { Box, CircularProgress, Skeleton, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';
import type { ParsedMarketplaceQuery } from '@/utils/marketplaceSearch';

import MarketplaceCard from './MarketplaceCard';
import type { MarketplaceFacets } from './MarketplaceFilterSidebar';
import MarketplaceFilterSidebar from './MarketplaceFilterSidebar';

interface MarketplaceBrowseProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  parsedQuery: ParsedMarketplaceQuery;
  facets: MarketplaceFacets;
  onToggleFilter: (field: string, value: string) => void;
  results: CatalogItem[];
  isLoading: boolean;
  isLoadingMore?: boolean;
  hasNextPage?: boolean;
  onLoadMore?: () => void;
  onSelect: (item: CatalogItem) => void;
}

export default function MarketplaceBrowse({
  searchQuery,
  onSearchChange,
  parsedQuery,
  facets,
  onToggleFilter,
  results,
  isLoading,
  isLoadingMore = false,
  hasNextPage = false,
  onLoadMore,
  onSelect,
}: Readonly<MarketplaceBrowseProps>) {
  const gridRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    const el = gridRef.current;
    if (!el || !hasNextPage || isLoadingMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 600) {
      onLoadMore?.();
    }
  }, [hasNextPage, isLoadingMore, onLoadMore]);

  return (
    <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      <MarketplaceFilterSidebar
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
        parsedQuery={parsedQuery}
        facets={facets}
        onToggleFilter={onToggleFilter}
      />

      <Box ref={gridRef} onScroll={handleScroll} sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading ? (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: 2,
              p: 3,
            }}
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton
                key={i}
                variant="rounded"
                height={130}
                sx={{ bgcolor: 'var(--bg-secondary)' }}
              />
            ))}
          </Box>
        ) : results.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              {searchQuery ? 'No results found' : 'No items available'}
            </Typography>
          </Box>
        ) : (
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: 2,
              p: 3,
              alignContent: 'start',
            }}
          >
            {results.map((item) => (
              <MarketplaceCard key={item.laui} item={item} onClick={onSelect} />
            ))}
          </Box>
        )}
        {isLoadingMore && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={20} sx={{ color: 'var(--accent)' }} />
          </Box>
        )}
      </Box>
    </Box>
  );
}
