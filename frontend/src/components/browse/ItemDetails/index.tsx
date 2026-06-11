/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect } from 'react';

import { Box, Typography } from '@mui/material';

import MarkdownRenderer from '@/components/browse/MarkdownRenderer';
import TaskView from '@/components/browse/TaskDetails/TaskView';
import { useCatalog } from '@/contexts/CatalogContext';

import CatalogItemSidebar from '../TabView/CatalogItemSidebar';
import TabView from '../TabView/TabView';
import FolderView from './FolderView';
import ItemsView from './ItemsView';

const styles = {
  content: {
    p: 3,
  },
  title: {
    color: 'var(--text-primary)',
    fontWeight: 'semibold',
    mb: 1,
  },
  description: {
    color: 'var(--text-secondary)',
    mb: 2,
  },
  listTitle: {
    color: 'var(--text-primary)',
    fontWeight: 'semibold',
    mb: 2,
    fontSize: '1.125rem',
  },
  listItem: {
    py: 1.5,
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
    },
  },
  itemName: {
    color: 'var(--text-primary)',
    fontWeight: 'medium',
  },
  itemDescription: {
    color: 'var(--text-secondary)',
    fontSize: '0.875rem',
    mt: 0.5,
  },
  itemType: {
    color: 'var(--text-secondary)',
    fontSize: '0.75rem',
    fontStyle: 'italic',
    opacity: 0.8,
  },
  container: {
    flex: 1,
    bgcolor: 'var(--bg-primary)',
    overflow: 'auto',
  },
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-secondary)',
  },
};

function EditorView({ viewingItem, formMode, editingItem }: any) {
  if (viewingItem?.item_type === 'task') {
    return <TaskView selectedItem={viewingItem} />;
  }
  const itemForSidebar = formMode === 'edit' ? editingItem : viewingItem;
  return (
    <TabView sidebar={itemForSidebar ? <CatalogItemSidebar item={itemForSidebar} /> : undefined} />
  );
}

export default function ItemDetails() {
  const { editorState, catalogState } = useCatalog();
  const { isEditorActive, viewingItem, formMode, editingItem } = editorState;
  const {
    selectedItem,
    filteredItemsByType,
    activeFilterType,
    filteredFromItem,
    setIsBreadcrumbLocked,
  } = catalogState;

  useEffect(() => {
    setIsBreadcrumbLocked(false);
  }, []);

  if (isEditorActive) {
    return <EditorView viewingItem={viewingItem} formMode={formMode} editingItem={editingItem} />;
  }

  if (selectedItem?.item_type === 'doc.file') {
    const docItem = viewingItem?.item_type === 'doc.file' ? viewingItem : selectedItem;
    const content = docItem?.data?.description ?? '';
    return (
      <Box sx={{ overflow: 'auto', height: '100%' }}>
        <MarkdownRenderer content={content} showToc />
      </Box>
    );
  }

  // filteredFromItem fallback handles the case where selectedItem is temporarily null
  // during sort/pagination (loadChildrenByType clears selectedItem) while still inside a folder
  if (
    selectedItem?.item_type?.startsWith('folder') ||
    filteredFromItem?.item_type?.startsWith('folder')
  ) {
    return <FolderView />;
  }

  if (filteredItemsByType && activeFilterType) {
    return <ItemsView />;
  }

  return (
    <Box sx={styles.container}>
      <Box sx={styles.emptyState}>
        <Typography variant="h6">Select an item to view details</Typography>
      </Box>
    </Box>
  );
}
