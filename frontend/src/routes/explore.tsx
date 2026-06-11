/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback } from 'react';

import { createFileRoute, useNavigate, useSearch } from '@tanstack/react-router';

import { CatalogProvider } from '@/contexts/CatalogContext';
import ReportExplorer from '@/screens/ReportExplorer';

export const Route = createFileRoute('/explore')({
  component: ExploreRouteComponent,
  validateSearch: (search: Record<string, unknown>) => ({
    laui: typeof search.laui === 'string' ? search.laui : undefined,
    path: typeof search.path === 'string' ? search.path : undefined,
    report: typeof search.report === 'string' ? search.report : undefined,
  }),
});

function ExploreRouteComponent() {
  const { laui, report } = useSearch({ from: '/explore' });
  const navigate = useNavigate();

  const handleFolderChange = useCallback(
    (folderLaui: string | null, path?: string) => {
      void navigate({
        from: '/explore',
        to: '/explore',
        search: folderLaui
          ? { laui: folderLaui, path: path || undefined, report: undefined }
          : { laui: undefined, path: undefined, report: undefined },
      });
    },
    [navigate],
  );

  const handleReportChange = useCallback(
    (reportLaui: string | null) => {
      void navigate({
        from: '/explore',
        to: '/explore',
        search: (prev) =>
          reportLaui ? { ...prev, report: reportLaui } : { ...prev, report: undefined },
      });
    },
    [navigate],
  );

  return (
    <CatalogProvider>
      <ReportExplorer
        initialLaui={laui}
        initialReportLaui={report}
        onFolderChange={handleFolderChange}
        onReportChange={handleReportChange}
      />
    </CatalogProvider>
  );
}
