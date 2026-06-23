/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// components/Browse/ItemsView.tsx
import { useEffect, useState } from 'react';

import {
  ArrowDropDown,
  SaveAlt as CreateIcon,
  CloudUpload as PublishIcon,
} from '@mui/icons-material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
  Box,
  Button,
  CircularProgress,
  Collapse,
  IconButton,
  LinearProgress,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';

import LinkedItemRow from '@/components/browse/modals/LinkedItemRow';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { useNotification } from '@/contexts/NotificationContext';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import { usePaginationHandlers } from '@/screens/Browse/handlers/paginationHandlers';
import {
  deleteCatalogItem,
  searchCatalogItems,
  searchCatalogLinks,
} from '@/services/catalog.service';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS, TASK_STATE_COLORS } from '../../../constants';
import BulkPublishUsecaseModal from '../modals/BulkPublishUsecaseModal';
import CreateItemButton from './CreateItemButton';
import ItemsTable from './ItemsTable';

const styles = {
  container: {
    flex: 1,
    bgcolor: 'var(--bg-primary)',
    overflow: 'auto',
  },
  content: {
    p: 3,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mb: 2,
  },
  listTitle: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.SEMIBOLD,
    fontSize: FONT_SIZES.BASE,
  },
};

interface ItemsViewProps {
  /** When true, the task table groups & tints tasks by their dependency DAG (workflow Tasks tab). */
  dependencyGrouping?: boolean;
}

/**
 * ItemsView - Displays a list/table of filtered catalog items
 */
export default function ItemsView({ dependencyGrouping }: ItemsViewProps = {}) {
  const { trashLaui, catalogType } = useGlobal();
  const { catalogState } = useCatalog();
  const { setTaskModalState } = useTaskModalContext();
  const { handleCreateNewItem } = useEditorHandlers();
  const { handleRefreshFilteredList, refreshFilteredList } = usePaginationHandlers();
  const { showSuccess } = useNotification();
  const { publishAccess } = useMarketplace();

  const filterType = catalogState.activeFilterType;
  const filteredItems = catalogState.filteredItemsByType;
  const filteredFromItem = catalogState.filteredFromItem;
  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const [taskStats, setTaskStats] = useState<{
    total: number;
    scheduled: number;
    running: number;
    success: number;
    error: number;
    cancelled: number;
  } | null>(null);

  useEffect(() => {
    if (filterType !== 'task' || !filteredFromItem?.laui || filteredFromItem?.laui === trashLaui)
      return;
    searchCatalogItems('task', false, {
      filters: { parent_laui: filteredFromItem.laui },
      projection: ['name', 'state'],
      perPage: 1000,
    })
      .then((data) => {
        const items: any[] = data.items ?? [];
        const countByState = (state: string) =>
          items.filter((i) => (i.data?.state || i.state) === state).length;
        setTaskStats({
          total: items.length,
          scheduled: countByState('scheduled'),
          running: countByState('running'),
          success: countByState('success'),
          error: countByState('error'),
          cancelled: countByState('cancelled'),
        });
      })
      .catch(() => {});
  }, [filterType, filteredFromItem?.laui]);

  const [selectedItems, setSelectedItems] = useState<string[]>([]);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [bulkPublishOpen, setBulkPublishOpen] = useState(false);
  const [usecaseMode, setUsecaseMode] = useState<'create' | 'create_and_publish'>('create');
  const [usecaseMenuAnchor, setUsecaseMenuAnchor] = useState<null | HTMLElement>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteProgress, setDeleteProgress] = useState(0);
  const [linkedItemsMap, setLinkedItemsMap] = useState<Record<string, any[]>>({});
  const [linkedItemsLoading, setLinkedItemsLoading] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({});

  const deletePermission =
    filteredFromItem &&
    ['own', 'edit'].includes(filteredFromItem.permission || '') &&
    !filteredFromItem.deleted_at;
  const isTrashView = filteredFromItem?.laui === trashLaui;

  const handleBulkDelete = async () => {
    if (!filteredFromItem) return;
    const parentLaui = filteredFromItem.laui;
    const total = selectedItems.length;
    setIsDeleting(true);
    setDeleteProgress(0);
    let successCount = 0,
      failCount = 0;
    for (let i = 0; i < total; i++) {
      try {
        await deleteCatalogItem(selectedItems[i], parentLaui);
        successCount++;
      } catch {
        failCount++;
      }
      setDeleteProgress(Math.round(((i + 1) / total) * 100));
    }
    setIsDeleting(false);
    setBulkDeleteOpen(false);
    if (failCount === 0) showSuccess(`Deleted ${successCount} item(s) successfully`);
    void handleRefreshFilteredList();
    setSelectedItems([]);
  };

  if (!filterType) return;

  const handleCreateItem = async () => {
    if (filterType === 'task') {
      const isUnderWorkflow = filteredFromItem?.item_type?.includes('workflow');
      setTaskModalState({
        isOpen: true,
        mode: TaskModalMode.CREATE,
        scope: { scopeType: TaskModalScopeType.DEFAULT },
        onSuccess: () => void refreshFilteredList(),
        ...(isUnderWorkflow && filteredFromItem?.laui
          ? { initialTaskData: { workflow_laui: filteredFromItem.laui } }
          : {}),
      });
      return;
    }
    // For other items, use the form-based create
    //console.log('Creating new item from ItemsView, filterType:', filterType);
    await handleCreateNewItem(filterType);
  };

  const isTaskView = filterType === 'task';

  return (
    <Box sx={styles.container}>
      <Box sx={styles.content}>
        {isTaskView ? (
          <>
            {/* Task Management Header */}
            <Box
              sx={{
                mb: 2,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
              }}
            >
              <Box>
                <Typography
                  sx={{
                    fontSize: '1.5rem',
                    fontWeight: FONT_WEIGHTS.BOLD,
                    color: 'var(--text-primary)',
                    mb: 0.5,
                  }}
                >
                  Task Management
                </Typography>
                <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
                  Monitor and orchestrate pipeline executions in real-time.
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Tooltip title="Refresh table">
                  <IconButton
                    onClick={() => void handleRefreshFilteredList()}
                    size="small"
                    data-tour-target="refresh-table-button"
                    sx={{
                      color: 'var(--text-primary)',
                      '&:hover': { bgcolor: 'var(--bg-secondary)' },
                    }}
                  >
                    <RefreshIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                {deletePermission && selectedItems.length > 0 && (
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<DeleteIcon />}
                    onClick={() => {
                      void (async () => {
                        setBulkDeleteOpen(true);
                        setLinkedItemsMap({});
                        setExpandedItems({});
                        setLinkedItemsLoading(true);
                        try {
                          const results: Record<string, any[]> = {};
                          await Promise.all(
                            selectedItems.map(async (laui) => {
                              const linksResponse = await searchCatalogLinks({
                                child_laui: laui,
                                true_parent: 'false',
                              });
                              const links = linksResponse.links || [];
                              if (links.length > 0) {
                                const parentLauis = links.map((l: any) => l.parent_laui);
                                const itemsResponse = await searchCatalogItems(undefined, false, {
                                  filters: {
                                    item_lauis: parentLauis,
                                  },
                                });
                                results[laui] = itemsResponse.items || [];
                              } else {
                                results[laui] = [];
                              }
                            }),
                          );
                          setLinkedItemsMap(results);
                        } catch (err) {
                          console.error('Error fetching linked items:', err);
                        } finally {
                          setLinkedItemsLoading(false);
                        }
                      })();
                    }}
                    sx={{
                      borderColor: 'var(--error-main)',
                      color: 'var(--error-main)',
                      textTransform: 'none',
                      fontSize: FONT_SIZES.SM,
                      '&:hover': {
                        borderColor: 'var(--error-dark)',
                        bgcolor: 'rgba(211,47,47,0.08)',
                      },
                    }}
                  >
                    {`Delete (${selectedItems.length})`}
                  </Button>
                )}
                {deletePermission && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => void handleCreateItem()}
                    data-tour-target="create-item-button"
                    sx={{
                      bgcolor: 'var(--text-primary)',
                      color: 'var(--bg-primary)',
                      textTransform: 'none',
                      fontWeight: FONT_WEIGHTS.SEMIBOLD,
                      fontSize: FONT_SIZES.SM,
                      borderRadius: BORDER_RADIUS.MD,
                      boxShadow: 'none',
                      '&:hover': {
                        bgcolor: 'var(--text-primary)',
                        opacity: 0.88,
                        boxShadow: 'none',
                      },
                    }}
                  >
                    Add Task
                  </Button>
                )}
              </Box>
            </Box>

            {/* Stats Cards */}
            {!isTrashView && (
              <Box sx={{ display: 'flex', gap: 1.5, mb: 2, flexWrap: 'wrap' }}>
                {[
                  {
                    label: 'Total Tasks',
                    value: taskStats?.total ?? 0,
                    color: 'var(--text-primary)',
                  },
                  {
                    label: 'Scheduled',
                    value: taskStats?.scheduled ?? 0,
                    color: TASK_STATE_COLORS.scheduled.text,
                  },
                  {
                    label: 'Running',
                    value: taskStats?.running ?? 0,
                    color: TASK_STATE_COLORS.running.text,
                  },
                  {
                    label: 'Success',
                    value: taskStats?.success ?? 0,
                    color: TASK_STATE_COLORS.success.text,
                  },
                  {
                    label: 'Error',
                    value: taskStats?.error ?? 0,
                    color: TASK_STATE_COLORS.error.text,
                  },
                  {
                    label: 'Cancelled',
                    value: taskStats?.cancelled ?? 0,
                    color: TASK_STATE_COLORS.cancelled.text,
                  },
                ].map((stat) => (
                  <Box
                    key={stat.label}
                    sx={{
                      flex: '1 1 100px',
                      p: 2,
                      borderRadius: BORDER_RADIUS.LG,
                      bgcolor: 'var(--bg-secondary)',
                      border: 1,
                      borderColor: 'var(--border)',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        fontWeight: FONT_WEIGHTS.WEIGHT_600,
                        color: 'var(--text-secondary)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        mb: 0.5,
                      }}
                    >
                      {stat.label}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: '1.75rem',
                        fontWeight: FONT_WEIGHTS.BOLD,
                        color: stat.color,
                        lineHeight: 1.2,
                      }}
                    >
                      {stat.value.toLocaleString()}
                    </Typography>
                  </Box>
                ))}
              </Box>
            )}
          </>
        ) : (
          <Box sx={styles.header}>
            <Typography sx={styles.listTitle}>
              {`${filterType === '__folder__' ? 'Folder' : filterType} Items (${filteredItems.length})`}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Tooltip title="Refresh table">
                <IconButton
                  onClick={() => void handleRefreshFilteredList()}
                  size="small"
                  sx={{
                    color: 'var(--text-primary)',
                    '&:hover': { bgcolor: 'var(--bg-secondary)' },
                  }}
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              {deletePermission && selectedItems.length > 0 && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DeleteIcon />}
                  onClick={() => {
                    void (async () => {
                      setBulkDeleteOpen(true);
                      setLinkedItemsMap({});
                      setExpandedItems({});
                      setLinkedItemsLoading(true);
                      try {
                        const results: Record<string, any[]> = {};
                        await Promise.all(
                          selectedItems.map(async (laui) => {
                            const linksResponse = await searchCatalogLinks({
                              child_laui: laui,
                              true_parent: 'false',
                            });
                            const links = linksResponse.links || [];
                            if (links.length > 0) {
                              const parentLauis = links.map((l: any) => l.parent_laui);
                              const itemsResponse = await searchCatalogItems(undefined, false, {
                                filters: {
                                  item_lauis: parentLauis,
                                },
                              });
                              results[laui] = itemsResponse.items || [];
                            } else {
                              results[laui] = [];
                            }
                          }),
                        );
                        setLinkedItemsMap(results);
                      } catch (err) {
                        console.error('Error fetching linked items:', err);
                      } finally {
                        setLinkedItemsLoading(false);
                      }
                    })();
                  }}
                  sx={{
                    borderColor: 'var(--error-main)',
                    color: 'var(--error-main)',
                    textTransform: 'none',
                    fontSize: FONT_SIZES.SM,
                    '&:hover': {
                      borderColor: 'var(--error-dark)',
                      bgcolor: 'rgba(211,47,47,0.08)',
                    },
                  }}
                >
                  {`Delete (${selectedItems.length})`}
                </Button>
              )}
              {!isMarketplaceCatalog &&
                (filterType === 'payload' ||
                  filterType === 'skill' ||
                  filteredItems.some(
                    (i) => i.item_type === 'payload' || i.item_type === 'skill',
                  )) &&
                selectedItems.length > 0 && (
                  <>
                    <Button
                      variant="outlined"
                      size="small"
                      endIcon={<ArrowDropDown />}
                      onClick={(e) => setUsecaseMenuAnchor(e.currentTarget)}
                      sx={{
                        borderColor: '#4caf50',
                        color: '#4caf50',
                        textTransform: 'none',
                        fontSize: FONT_SIZES.SM,
                        '&:hover': {
                          borderColor: '#388e3c',
                          bgcolor: 'rgba(76,175,80,0.08)',
                        },
                      }}
                    >
                      {`Usecase (${selectedItems.length})`}
                    </Button>
                    <Menu
                      anchorEl={usecaseMenuAnchor}
                      open={Boolean(usecaseMenuAnchor)}
                      onClose={() => setUsecaseMenuAnchor(null)}
                      slotProps={{
                        paper: {
                          sx: {
                            bgcolor: 'var(--bg-secondary)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border)',
                          },
                        },
                      }}
                    >
                      <MenuItem
                        onClick={() => {
                          setUsecaseMode('create');
                          setBulkPublishOpen(true);
                          setUsecaseMenuAnchor(null);
                        }}
                      >
                        <ListItemIcon>
                          <CreateIcon
                            sx={{
                              fontSize: 16,
                              color: 'var(--text-secondary)',
                            }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primaryTypographyProps={{
                            fontSize: FONT_SIZES.SM,
                          }}
                        >
                          Create Usecase
                        </ListItemText>
                      </MenuItem>
                      <MenuItem
                        disabled={!publishAccess}
                        onClick={() => {
                          setUsecaseMode('create_and_publish');
                          setBulkPublishOpen(true);
                          setUsecaseMenuAnchor(null);
                        }}
                      >
                        <ListItemIcon>
                          <PublishIcon
                            sx={{
                              fontSize: 16,
                              color: publishAccess
                                ? 'var(--text-secondary)'
                                : 'var(--text-disabled)',
                            }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          primaryTypographyProps={{
                            fontSize: FONT_SIZES.SM,
                          }}
                          secondaryTypographyProps={{
                            fontSize: FONT_SIZES.XS,
                          }}
                          secondary={!publishAccess ? 'Marketplace login required' : undefined}
                        >
                          Create & Publish Usecase
                        </ListItemText>
                      </MenuItem>
                    </Menu>
                  </>
                )}
              {deletePermission && (
                <CreateItemButton
                  onClick={() => void handleCreateItem()}
                  filterType={filterType === '__folder__' ? 'item' : filterType}
                />
              )}
            </Box>
          </Box>
        )}

        <ItemsTable onSelectionChange={setSelectedItems} dependencyGrouping={dependencyGrouping} />

        <BaseModal
          open={bulkDeleteOpen}
          onClose={() => {
            if (!isDeleting) setBulkDeleteOpen(false);
          }}
          title="Confirm Bulk Delete"
          subtitle={
            Object.values(linkedItemsMap).some((arr) => arr.length > 0)
              ? 'Potential impact on linked items'
              : 'Move items to trash'
          }
          maxWidth="xs"
          actions={
            <>
              <Button
                onClick={() => setBulkDeleteOpen(false)}
                disabled={isDeleting}
                size="small"
                variant="outlined"
                sx={{
                  color: 'var(--text-secondary)',
                  borderColor: 'var(--border)',
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => void handleBulkDelete()}
                disabled={isDeleting}
                size="small"
                variant="contained"
                startIcon={isDeleting ? <CircularProgress size={14} /> : <DeleteIcon />}
                sx={{
                  bgcolor: 'var(--error-main, #d32f2f)',
                  color: '#fff',
                  textTransform: 'none',
                  fontWeight: 'bold',
                  '&:hover': { bgcolor: '#b71c1c' },
                }}
              >
                {isDeleting
                  ? `Deleting... (${deleteProgress}%)`
                  : `Delete ${selectedItems.length} Item(s)`}
              </Button>
            </>
          }
        >
          <Box sx={{ mt: 1 }}>
            {isDeleting ? (
              <Box>
                <Typography sx={{ color: 'var(--text-secondary)', mb: 1, fontSize: '13px' }}>
                  Deleting items, please wait...
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={deleteProgress}
                  sx={{ borderRadius: 1, bgcolor: 'var(--bg-secondary)' }}
                />
              </Box>
            ) : (
              <Box>
                <Typography sx={{ color: 'var(--text-primary)', mb: 2 }}>
                  {isTrashView ? (
                    <>
                      Are you sure you want to <strong>permanently delete</strong>{' '}
                      <strong>{selectedItems.length} item(s)</strong>? This cannot be undone.
                    </>
                  ) : (
                    <>
                      Are you sure you want to move <strong>{selectedItems.length} item(s)</strong>{' '}
                      to trash?
                    </>
                  )}
                  {Object.values(linkedItemsMap).some((arr) => arr.length > 0) &&
                    ' Some items are linked with others. These links will be permanently deleted.'}
                </Typography>
                {linkedItemsLoading ? (
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      color: 'var(--text-secondary)',
                      fontSize: '13px',
                    }}
                  >
                    <CircularProgress size={14} />
                    <Typography
                      sx={{
                        fontSize: '13px',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      Checking for linked items...
                    </Typography>
                  </Box>
                ) : (
                  <Stack spacing={1}>
                    {selectedItems.map((laui) => {
                      const linked = linkedItemsMap[laui] || [];
                      if (linked.length === 0) return null;
                      const isExpanded = expandedItems[laui] ?? false;
                      return (
                        <Box
                          key={laui}
                          sx={{
                            borderLeft: '3px solid',
                            borderColor: 'error.main',
                            pl: 2,
                            py: 0.5,
                          }}
                        >
                          <Box
                            onClick={() =>
                              setExpandedItems((prev) => ({
                                ...prev,
                                [laui]: !isExpanded,
                              }))
                            }
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              cursor: 'pointer',
                              gap: 0.5,
                            }}
                          >
                            <Typography
                              sx={{
                                fontWeight: 'bold',
                                fontSize: '13px',
                                color: 'var(--text-primary)',
                                flex: 1,
                              }}
                            >
                              {laui} — {linked.length} linked item(s)
                            </Typography>
                            {isExpanded ? (
                              <ExpandLessIcon fontSize="small" />
                            ) : (
                              <ExpandMoreIcon fontSize="small" />
                            )}
                          </Box>
                          <Collapse in={isExpanded}>
                            <Stack spacing={1} sx={{ mt: 1 }}>
                              {linked.map((item, idx) => (
                                <LinkedItemRow key={item.laui || idx} item={item} index={idx} />
                              ))}
                            </Stack>
                          </Collapse>
                        </Box>
                      );
                    })}
                  </Stack>
                )}
              </Box>
            )}
          </Box>
        </BaseModal>

        <BulkPublishUsecaseModal
          open={bulkPublishOpen}
          onClose={() => setBulkPublishOpen(false)}
          selectedLauis={selectedItems}
          sourceType={
            filterType === 'skill' || filteredItems.some((i) => i.item_type === 'skill')
              ? 'skill'
              : 'payload'
          }
          parentLaui={filteredFromItem?.laui}
          mode={usecaseMode}
        />
      </Box>
    </Box>
  );
}
