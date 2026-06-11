/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useNavigate } from '@tanstack/react-router';

import type { CatalogItem } from '@/components/browse';
import { useCatalog } from '@/contexts/CatalogContext';

export function useNavigationHandlers() {
  const navigate = useNavigate();
  const { markNavigatedInAppRef } = useCatalog();

  const navigateToPath = (item: CatalogItem | null, filtertype?: string) => {
    if (!item || item.laui === 'shared') {
      void navigate({ to: '/' });
      return;
    }
    markNavigatedInAppRef.current?.(item.laui);
    void navigate({
      to: '/path',
      search: {
        itemtype: item.item_type ?? '',
        itemname: item.name ?? '',
        laui: item.laui,
        ...(filtertype ? { filtertype } : {}),
      },
    });
  };

  return { navigateToPath };
}
