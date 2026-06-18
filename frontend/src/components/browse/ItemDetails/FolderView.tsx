/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// components/Browse/ItemDetails/FolderView.tsx
import { useEffect, useState } from 'react';

import { Add as AddIcon, Edit as EditIcon } from '@mui/icons-material';
import { Box, Button, Tab, Tabs, Typography } from '@mui/material';

import type { TaskItem } from '@/components/browse/Flows/WorkflowDiagram';
import WorkflowDiagram from '@/components/browse/Flows/WorkflowDiagram';
import ItemsTable from '@/components/browse/ItemDetails/ItemsTable';
import ItemsView from '@/components/browse/ItemDetails/ItemsView';
import OtherActionsDropdown from '@/components/browse/TabView/OtherActionsDropdown';
import type { CatalogItem } from '@/components/browse/types';
import { TabPanel } from '@/components/ui';
import { useCatalog } from '@/contexts/CatalogContext';
import { useGlobal } from '@/contexts/GlobalContext';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import {
  getCatalogItemById,
  getChildCatalogNodes,
  getChildCatalogNodesByType,
  searchCatalogItems,
} from '@/services/catalog.service';
import { isDocItem } from '@/utils/docsTree';

import { BUTTON_SIZES, FONT_SIZES, FONT_WEIGHTS } from '../../../constants';
import MarkdownRenderer from '../MarkdownRenderer';
import AddItemDropdown from './AddItemDropdown';

const isTaskType = (t?: string) => t === 'task' || (t?.startsWith('task.') ?? false);

const actionButtonStyle = {
  borderColor: 'var(--border)',
  color: 'var(--text-secondary)',
  textTransform: 'none',
  fontSize: BUTTON_SIZES.FONT_SIZE,
  fontWeight: BUTTON_SIZES.FONT_WEIGHT,
  height: BUTTON_SIZES.HEIGHT,
  padding: BUTTON_SIZES.PADDING,
  borderRadius: BUTTON_SIZES.BORDER_RADIUS,
  '& .MuiSvgIcon-root': { fontSize: BUTTON_SIZES.ICON_FONT_SIZE },
  '&:hover': { borderColor: 'var(--accent)', color: 'var(--text-primary)' },
} as const;

const styles = {
  container: {
    flex: 1,
    bgcolor: 'var(--bg-primary)',
    overflow: 'auto',
    px: '6px',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    p: 0.5,
  },
  title: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.SEMIBOLD,
    mb: 1,
  },
  description: {
    color: 'var(--text-secondary)',
    mb: 2,
  },
};

export default function FolderView() {
  const { catalogState } = useCatalog();
  const { trashLaui } = useGlobal();
  const {
    selectedItem,
    setSelectedItem,
    setFilteredItemsByType,
    setActiveFilterType,
    setFilteredFromItem,
    activeWorkflowTab,
    setActiveWorkflowTab,
  } = catalogState;
  const { handleCreateNewItem, handleEditItem } = useEditorHandlers();

  // selectedItem may be temporarily null during sort/pagination; fall back to filteredFromItem
  const effectiveItem = selectedItem ?? catalogState.filteredFromItem;
  const isInTrash =
    effectiveItem?.item_type === 'folder.trash' ||
    effectiveItem?.laui === trashLaui ||
    !!effectiveItem?.deleted_at;
  const isWorkflowFolder = effectiveItem?.item_type === 'folder.workflow';

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState('');
  const [selectedFilterType, setSelectedFilterType] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [workflowTasks, setWorkflowTasks] = useState<TaskItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);

  const supportedTypes = effectiveItem?.supported_types || [];
  const filterOptions = supportedTypes.filter((t) => !(isWorkflowFolder && isTaskType(t)));

  // Fetch full item if supported_types not yet loaded.
  // Doc items are in-memory only (no ObjectId) — never hit the catalog API for them.
  useEffect(() => {
    if (!selectedItem?.laui || selectedItem.supported_types !== undefined) return;
    if (isDocItem(selectedItem.laui)) return;
    getCatalogItemById(selectedItem.laui)
      .then((fullItem) => setSelectedItem(fullItem as CatalogItem))
      .catch((err) => console.error('FolderView: failed to fetch full item', err));
  }, [selectedItem?.laui]);

  // Reset view state when folder changes
  useEffect(() => {
    setPage(1);
    setSelectedFilterType(null);
    setSearch('');
    setActiveWorkflowTab(0);
    setWorkflowTasks([]);
  }, [selectedItem?.laui, setActiveWorkflowTab]);

  // Reset page when filter, search, or per-page changes
  useEffect(() => {
    setPage(1);
  }, [selectedFilterType, perPage, search]);

  // Auto-load tasks for workflow folders when Tasks tab is viewed
  useEffect(() => {
    if (!isWorkflowFolder || !selectedItem?.laui || activeWorkflowTab !== 0) return;
    const perm = selectedItem.permission ?? 'view';
    let cancelled = false;
    setLoadingItems(true);
    getChildCatalogNodesByType(selectedItem.laui, 'task', perm, false, 1, 25)
      .then(({ items }) => {
        if (cancelled) return;
        setFilteredItemsByType(items.map((n) => n.item));
        setActiveFilterType('task');
        setFilteredFromItem(selectedItem);
      })
      .catch((err) => console.error('FolderView: failed to load workflow tasks', err))
      .finally(() => {
        if (!cancelled) setLoadingItems(false);
      });
    return () => {
      cancelled = true;
    };
  }, [
    selectedItem?.laui,
    selectedItem?.permission,
    activeWorkflowTab,
    isWorkflowFolder,
    setFilteredItemsByType,
    setActiveFilterType,
    setFilteredFromItem,
  ]);

  // Fetch children and push into catalogState so ItemsTable can render them.
  // For workflow folders, skip when on Tasks tab (tab 0) — the workflow-tasks effect handles that.
  useEffect(() => {
    if (!selectedItem?.laui) {
      if (!catalogState.filteredFromItem?.laui) {
        catalogState.setFilteredItemsByType([]);
        catalogState.setActiveFilterType(null);
        catalogState.setFilteredFromItem(null);
      }
      return;
    }
    // Wait for the full item: until supported_types is loaded we can't know
    // whether this is a workflow folder, and running early races the tasks effect
    if (selectedItem.supported_types === undefined) return;
    // Workflow folders on Tasks tab: skip — the tasks effect below populates state
    if (isWorkflowFolder && activeWorkflowTab === 0) return;

    const perm = selectedItem.permission ?? 'view';

    let cancelled = false;
    setLoadingItems(true);
    const doFetch = async () => {
      try {
        let items: CatalogItem[] = [];
        let hasNextPage = false;

        if (search.trim()) {
          const filters: Record<string, string> = {
            parent_laui: selectedItem.laui,
            name: search.trim(),
          };
          if (selectedFilterType) filters.item_type = selectedFilterType;
          const result = await searchCatalogItems(undefined, false, {
            filters,
            perPage,
            page,
          });
          const rawItems = (result?.items ?? []) as any[];
          items = rawItems.map((n: any) => n.item ?? n) as CatalogItem[];
          hasNextPage = result?.pagination?.has_next ?? false;
        } else if (!selectedFilterType) {
          const { items: nodes, pagination } = await getChildCatalogNodes(
            selectedItem.laui,
            perm,
            false,
            page,
            perPage,
          );
          const filtered = isWorkflowFolder
            ? nodes.filter((n) => !isTaskType(n.item.item_type))
            : nodes;
          items = filtered.map((n) => n.item);
          hasNextPage = pagination?.has_next ?? false;
        } else if (selectedFilterType === 'folder') {
          const { items: nodes, pagination } = await getChildCatalogNodes(
            selectedItem.laui,
            perm,
            false,
            page,
            perPage,
            'folder',
          );
          items = nodes.map((n) => n.item);
          hasNextPage = pagination?.has_next ?? false;
        } else {
          const { items: nodes, pagination } = await getChildCatalogNodesByType(
            selectedItem.laui,
            selectedFilterType,
            perm,
            false,
            page,
            perPage,
          );
          items = nodes.map((n) => n.item);
          hasNextPage = pagination?.has_next ?? false;
        }

        if (cancelled) return;
        catalogState.setFilteredItemsByType(items);
        catalogState.setFilteredItemsPagination({
          current_page: page,
          per_page: perPage,
          has_next: hasNextPage,
          has_previous: page > 1,
        });
        catalogState.setActiveFilterType(selectedFilterType ?? '__folder__');
        catalogState.setFilteredFromItem(selectedItem);
      } catch (err) {
        console.error('FolderView: failed to fetch children', err);
        if (!cancelled) catalogState.setFilteredItemsByType([]);
      } finally {
        if (!cancelled) setLoadingItems(false);
      }
    };

    void doFetch();
    return () => {
      cancelled = true;
    };
  }, [
    selectedItem?.laui,
    selectedFilterType,
    page,
    perPage,
    refreshKey,
    isWorkflowFolder,
    search,
    activeWorkflowTab,
  ]);

  // For workflow folders: also populate task context for ItemsView (Tasks tab)
  useEffect(() => {
    if (!isWorkflowFolder) {
      return;
    }
    if (!selectedItem?.laui) return;
    const perm = selectedItem.permission ?? 'view';
    let cancelled = false;
    setLoadingItems(true);
    getChildCatalogNodesByType(selectedItem.laui, 'task', perm, false, 1, 25)
      .then(({ items, pagination }) => {
        if (cancelled) return;
        const taskItems = items.map((n) => n.item);
        catalogState.setFilteredItemsByType(taskItems);
        catalogState.setFilteredItemsPagination(pagination ?? null);
        catalogState.setActiveFilterType('task');
        catalogState.setFilteredFromItem(selectedItem);
        setWorkflowTasks(taskItems as unknown as TaskItem[]);
      })
      .catch((err) => console.error('FolderView: failed to fetch tasks', err))
      .finally(() => {
        if (!cancelled) setLoadingItems(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedItem?.laui, isWorkflowFolder, refreshKey]);

  const canAdd =
    !isInTrash &&
    supportedTypes.length > 0 &&
    !effectiveItem?.deleted_at &&
    ['own', 'edit'].includes(effectiveItem?.permission ?? '');

  const handleDeleteSuccess = () => setRefreshKey((k) => k + 1);

  const renderHeader = () => (
    <Box
      sx={{
        px: 2.5,
        py: 2,
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: 2,
        bgcolor: 'var(--bg-secondary)',
      }}
    >
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="h6" sx={styles.title}>
          {effectiveItem?.data?.name || effectiveItem?.name || 'Unnamed'}
        </Typography>
        <Box sx={styles.description}>
          <MarkdownRenderer
            content={effectiveItem?.data?.description || effectiveItem?.description || ''}
          />
        </Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
        {canAdd && (
          <Box sx={styles.headerRight}>
            <AddItemDropdown
              types={filterOptions}
              onSelect={(type) => void handleCreateNewItem(type)}
            />
          </Box>
        )}
        {isWorkflowFolder && canAdd && filterOptions.includes('config') && (
          <Box sx={styles.headerRight}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<AddIcon sx={{ fontSize: BUTTON_SIZES.ICON_FONT_SIZE }} />}
              onClick={() => void handleCreateNewItem('config')}
              sx={actionButtonStyle}
            >
              Add Config
            </Button>
          </Box>
        )}
        {!isInTrash &&
          selectedItem &&
          ['own', 'edit'].includes(selectedItem.permission) &&
          !selectedItem.deleted_at && (
            <Box sx={styles.headerRight}>
              <Button
                onClick={() => void handleEditItem(selectedItem)}
                size="small"
                variant="outlined"
                startIcon={<EditIcon />}
                sx={actionButtonStyle}
              >
                Edit
              </Button>
            </Box>
          )}
        {!isInTrash && (
          <Box sx={styles.headerRight}>
            <OtherActionsDropdown item={selectedItem} />
          </Box>
        )}
      </Box>
    </Box>
  );

  const renderItemsSection = () => (
    <ItemsTable
      folderMode
      folderSearchValue={search}
      onFolderSearchChange={setSearch}
      folderTypeOptions={filterOptions}
      folderTypeValue={selectedFilterType}
      onFolderTypeChange={setSelectedFilterType}
      onPageChange={setPage}
      onPerPageChange={setPerPage}
      folderParentLaui={effectiveItem?.laui}
      onDeleteSuccess={handleDeleteSuccess}
      onUsecaseCreateSuccess={handleDeleteSuccess}
      loadingItems={loadingItems}
    />
  );

  if (isWorkflowFolder) {
    return (
      <Box sx={styles.container}>
        <Box
          sx={{
            borderBottom: 1,
            borderColor: 'var(--border)',
            overflowX: 'auto',
            bgcolor: 'var(--bg-secondary)',
            '&::-webkit-scrollbar': { height: '3px' },
            '&::-webkit-scrollbar-track': { background: 'var(--bg-secondary)' },
            '&::-webkit-scrollbar-thumb': {
              background: 'var(--border)',
              borderRadius: '2px',
            },
          }}
        >
          <Tabs
            value={activeWorkflowTab}
            onChange={(_, v) => setActiveWorkflowTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              minHeight: '32px',
              '& .MuiTab-root': {
                color: 'var(--text-secondary)',
                textTransform: 'none',
                fontSize: FONT_SIZES.XS,
                fontWeight: FONT_WEIGHTS.WEIGHT_400,
                minHeight: '32px',
                minWidth: 'auto',
                px: 2,
                py: 0,
                '&.Mui-selected': {
                  color: 'var(--accent)',
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                },
              },
              '& .MuiTabs-indicator': { bgcolor: 'var(--accent)', height: '2px' },
            }}
          >
            <Tab label="Tasks" />
            <Tab label="Graph" />
            <Tab label="Items" />
          </Tabs>
        </Box>

        <TabPanel value={activeWorkflowTab} index={0}>
          <ItemsView />
        </TabPanel>

        <TabPanel value={activeWorkflowTab} index={1}>
          <Box sx={{ p: 2 }}>
            <WorkflowDiagram
              tasks={workflowTasks}
              workflowLaui={selectedItem?.laui}
              height={600}
              onTaskCreated={() => setRefreshKey((k) => k + 1)}
            />
          </Box>
        </TabPanel>

        <TabPanel value={activeWorkflowTab} index={2}>
          {renderHeader()}
          {renderItemsSection()}
        </TabPanel>
      </Box>
    );
  }

  return (
    <Box sx={styles.container}>
      <Box
        sx={{
          px: 2.5,
          py: 2,
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 2,
          bgcolor: 'var(--bg-secondary)',
          mt: 1,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h6" sx={styles.title}>
            {effectiveItem?.data?.name || effectiveItem?.name || 'Unnamed'}
          </Typography>
          <Box sx={styles.description}>
            <MarkdownRenderer
              content={effectiveItem?.data?.description || effectiveItem?.description || ''}
            />
          </Box>
        </Box>
        {canAdd && (
          <Box sx={styles.headerRight}>
            <AddItemDropdown
              types={filterOptions}
              onSelect={(type) => void handleCreateNewItem(type)}
            />
          </Box>
        )}
        {!isInTrash &&
          selectedItem &&
          ['own', 'edit'].includes(selectedItem.permission) &&
          !selectedItem.deleted_at && (
            <Box sx={styles.headerRight}>
              <Button
                onClick={() => void handleEditItem(selectedItem)}
                size="small"
                variant="outlined"
                startIcon={<EditIcon />}
                sx={actionButtonStyle}
              >
                Edit
              </Button>
            </Box>
          )}
        {!isInTrash && (
          <Box sx={styles.headerRight}>
            <OtherActionsDropdown item={selectedItem} />
          </Box>
        )}
      </Box>

      {renderItemsSection()}
    </Box>
  );
}
