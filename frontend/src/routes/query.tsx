/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute } from '@tanstack/react-router';

import { Box } from '@mui/material';

import { LeftSidebar, TopHeader } from '@/components/browse';
import { CatalogProvider } from '@/contexts/CatalogContext';
import QueryEditor from '@/screens/QueryEditor';

export const Route = createFileRoute('/query')({
  component: QueryRouteComponent,
});

function QueryRouteComponent() {
  return (
    <CatalogProvider>
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
          <Box
            sx={{
              flex: 1,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <QueryEditor />
          </Box>
        </Box>
      </Box>
    </CatalogProvider>
  );
}
