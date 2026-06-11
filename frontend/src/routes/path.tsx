/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute, useSearch } from '@tanstack/react-router';

import { CatalogProvider } from '@/contexts/CatalogContext';

import Browse from '../screens/Browse/index';

interface PathSearchParams {
  itemtype?: string;
  itemname?: string;
  laui?: string;
  filtertype?: string;
  page?: number;
  perPage?: number;
  sortBy?: string;
  sortOrder?: string;
  filterState?: string;
  tab?: string;
  itemTab?: string;
  sessionId?: string;
}

export const Route = createFileRoute('/path')({
  component: PathRouteComponent,
  validateSearch: (search: Record<string, unknown>): PathSearchParams => {
    return {
      itemtype: typeof search.itemtype === 'string' ? search.itemtype : undefined,
      itemname: typeof search.itemname === 'string' ? search.itemname : undefined,
      laui: typeof search.laui === 'string' ? search.laui : undefined,
      filtertype: typeof search.filtertype === 'string' ? search.filtertype : undefined,
      page: search.page ? Number(search.page) : undefined,
      perPage: search.perPage ? Number(search.perPage) : undefined,
      sortBy: typeof search.sortBy === 'string' ? search.sortBy : undefined,
      sortOrder: typeof search.sortOrder === 'string' ? search.sortOrder : undefined,
      filterState: typeof search.filterState === 'string' ? search.filterState : undefined,
      tab: typeof search.tab === 'string' ? search.tab : undefined,
      itemTab: typeof search.itemTab === 'string' ? search.itemTab : undefined,
      sessionId: typeof search.sessionId === 'string' ? search.sessionId : undefined,
    };
  },
});

function PathRouteComponent() {
  const search = useSearch({ from: '/path' });
  return (
    <CatalogProvider>
      <Browse
        deepLinkItemType={search.itemtype}
        deepLinkItemName={search.itemname}
        deepLinkLaui={search.laui}
        deepLinkFilterType={search.filtertype}
        deepLinkPage={search.page}
        deepLinkPerPage={search.perPage}
        deepLinkSortBy={search.sortBy}
        deepLinkSortOrder={search.sortOrder as 'asc' | 'desc' | undefined}
        deepLinkTab={search.tab}
      />
    </CatalogProvider>
  );
}
