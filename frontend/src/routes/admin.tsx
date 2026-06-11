/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createFileRoute } from '@tanstack/react-router';

import { Box } from '@mui/material';

import AdminDashboard from '@/components/admin/Dashboard';
import { LeftSidebar, TopHeader } from '@/components/browse';

export const Route = createFileRoute('/admin')({
  component: RouteComponent,
});
const styles = {
  container: {
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  content: {
    flex: 1,
    overflow: 'auto', // scroll inside content
  },
};

function RouteComponent() {
  return (
    <>
      <Box sx={styles.container}>
        <TopHeader />
        <Box sx={styles.mainContent}>
          <LeftSidebar />
          <Box sx={styles.content}>
            <AdminDashboard />
          </Box>
        </Box>
      </Box>
    </>
  );
}
