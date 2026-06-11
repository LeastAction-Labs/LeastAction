/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import UnfoldLessIcon from '@mui/icons-material/UnfoldLess';
import UnfoldMoreIcon from '@mui/icons-material/UnfoldMore';
import { Box, Button, CircularProgress, Tab, Tabs } from '@mui/material';

import type { CatalogItem } from '@/components/browse';
import {
  Breadcrumbs,
  FolderSidebar,
  ItemDetails,
  LeftSidebar,
  TopHeader,
} from '@/components/browse';
import ChildItemsComponent from '@/components/browse/ChildItemsComponent/ChildItemsComponent';
import WorkflowDiagram from '@/components/browse/Flows/WorkflowDiagram';
import GroupsView from '@/components/browse/Groups/GroupsView';
import ItemTabBar from '@/components/browse/ItemTabBar/ItemTabBar';
import ParentItemsComponent from '@/components/browse/ParentItems/ParentItemsComponent';
import SchedulerTab from '@/components/browse/SchedulerTab';
import UsersGroupsTable from '@/components/browse/Users/UsersGroupsTable';
import DeleteModal from '@/components/browse/modals/DeleteModal';
import ImportModal from '@/components/browse/modals/ImportModal';
import LinkModal from '@/components/browse/modals/LinkModal';
import MarkdownModal from '@/components/browse/modals/MarkdownModal';
import { RestoreModal } from '@/components/browse/modals/RestoreModal';
import { SaveConfirmModal } from '@/components/browse/modals/SaveConfirmModal';
import ShareModal from '@/components/browse/modals/ShareModal';
import ActionVariablesModal from '@/components/modals/RunActionModal';
import RunTaskModal from '@/components/modals/RunTaskModal';
import { useActionContext } from '@/contexts/ActionContext';
import { useAuth } from '@/contexts/AuthContext';
import { CatalogMode, useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import {
  getCatalogItemById,
  getChildCatalogNodes,
  getRootCatalogNodes,
} from '@/services/catalog.service';

import { useDeepLink } from './hooks/useDeepLink';
import { getAttachedActions } from './utils';

export interface BrowseDeepLinkProps {
  deepLinkItemType?: string;
  deepLinkItemName?: string;
  deepLinkLaui?: string;
  deepLinkFilterType?: string;
  deepLinkPage?: number;
  deepLinkPerPage?: number;
  deepLinkSortBy?: string;
  deepLinkSortOrder?: 'asc' | 'desc';
  deepLinkTab?: string;
}

export default function Browse(props?: BrowseDeepLinkProps) {
  const {
    deepLinkItemType: itemtype,
    deepLinkItemName: itemname,
    deepLinkLaui: laui,
    deepLinkFilterType: filtertype,
    deepLinkPage: page,
    deepLinkPerPage: perPage,
    deepLinkSortBy: sortBy,
    deepLinkSortOrder: sortOrder,
    deepLinkTab,
  } = props ?? {};
  const navigate = useNavigate();
  const {
    catalogType,
    folderSidebarState,
    setFolderSidebarState,
    accountLaui,
    currentProjectLaui,
    setAccountLaui,
    setProjectLauis,
    setCurrentProjectLaui,
    setTrashLaui,
  } = useGlobal();
  const { catalogState, editorState, mode, markNavigatedInAppRef } = useCatalog();
  const { runActionModalData, setAttachedActions } = useActionContext();
  const { viewingItem } = editorState;
  const { authState } = useAuth();

  const [activeTab, setActiveTab] = useState<string>(deepLinkTab ?? 'details');
  const [drillDownOpen, setDrillDownOpen] = useState(false);
  const isProjectItem = !!catalogState.selectedItem?.item_type?.includes('project');

  const {
    setError,
    setIsLoading,
    setItems,
    setSelectedItem,
    setLoadedChildren,
    setExpandedItems,
    itemNotFound,
    isLoading,
    items,
  } = catalogState;

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  useEffect(() => {
    const loadItems = async () => {
      // Only load root items if user is authenticated
      if (authState.isAuthenticated) {
        try {
          setIsLoading(true);
          setError('');
          // Reset tree state so stale loadedChildren from a previous session
          // doesn't prevent children from being fetched after re-mount.
          setLoadedChildren(new Set());
          if (!laui) setExpandedItems(new Set());
          const { items: root } = await getRootCatalogNodes(isMarketplaceCatalog);
          setItems(root);
          if (root.length > 0 && root[0]?.item) {
            if (!laui) setSelectedItem(root[0].item);

            // Store account LAUI if root item is folder.account
            if (root[0].item.item_type === 'folder.account') {
              setAccountLaui(root[0].item.laui);
              // Mark account folder children as already loaded — backend pre-nests them in the root
              // response, so expandPathToItem must not re-fetch and overwrite with a paginated subset.
              setLoadedChildren((prev) => new Set([...prev, root[0].item.laui]));
              if (localStorage.getItem('la_account_laui') !== root[0].item.laui)
                localStorage.setItem('la_account_laui', root[0].item.laui);
              // Load children to get project LAUIs
              try {
                const { items: children } = await getChildCatalogNodes(
                  root[0].item.laui,
                  root[0].item.permission,
                  isMarketplaceCatalog,
                  1,
                  10,
                  'folder',
                );
                const projectLauis = children
                  .filter((child) => child.item.item_type === 'folder.project')
                  .map((child) => child.item.laui);
                setProjectLauis(projectLauis);
                if (!currentProjectLaui || !projectLauis.includes(currentProjectLaui)) {
                  setCurrentProjectLaui(projectLauis[0]);
                }
                if (localStorage.getItem('la_project_lauis') !== JSON.stringify(projectLauis))
                  localStorage.setItem('la_project_lauis', JSON.stringify(projectLauis));
                const trashLaui = children.find((child) => child.item.item_type === 'folder.trash')
                  ?.item.laui;
                setTrashLaui(trashLaui || null);
              } catch (error) {
                console.error('Error loading project LAUIs:', error);
              }
            }
          }
        } catch (e: unknown) {
          const message = e instanceof Error ? e.message : 'Failed to load items';
          setError(message);
        } finally {
          setIsLoading(false);
        }
      }
    };
    void loadItems();
  }, [catalogType, authState.isAuthenticated]);

  useEffect(() => {
    if (accountLaui && currentProjectLaui) return;
    if (items.length > 0 && items[0].item.item_type === 'folder.account') {
      setAccountLaui(items[0].item.laui);
      console.log('Set account LAUI from root item:', items[0].item.laui);
      const project = items[0].children.find((c) => c.item.item_type === 'folder.project');
      if (project) setCurrentProjectLaui(project.item.laui);
    }
  }, [items, accountLaui, currentProjectLaui]);

  const { markNavigatedInApp } = useDeepLink({
    itemtype,
    itemname,
    laui,
    filtertype,
    page,
    perPage,
    sortBy,
    sortOrder,
    isAuthReady: authState.isAuthenticated,
  });
  markNavigatedInAppRef.current = markNavigatedInApp;

  useEffect(() => {
    if (!deepLinkTab) setActiveTab('details');
    if (itemNotFound) catalogState.setItemNotFound(false);
  }, [catalogState.selectedItem?.laui]);

  useEffect(() => {
    if (activeTab !== 'graph') return;
    if (isLoading) return;
    if (!catalogState.openedFolder) return;
    if (!catalogState.openedFolder.item_type?.includes('workflow')) {
      setActiveTab('details');
      void navigate({
        to: '.',
        search: (prev: any) => ({ ...prev, tab: undefined }),
        replace: true,
      });
    }
  }, [catalogState.openedFolder, isLoading]);

  useEffect(() => {
    if (deepLinkTab) setActiveTab(deepLinkTab);
  }, [deepLinkTab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string) => {
    setActiveTab(newValue);
    void navigate({
      to: '.',
      search: (prev) => ({ ...prev, tab: newValue === 'details' ? undefined : newValue }),
      replace: true,
    });
    if (newValue === 'details') editorState.setFormMode('view');
    if (newValue === 'scheduler' && catalogState.selectedItem?.laui) {
      void getCatalogItemById(catalogState.selectedItem.laui).then((updatedData) => {
        catalogState.setSelectedItem(updatedData as CatalogItem);
      });
    }
  };

  // Load workflow actions when a folder.workflow is selected
  useEffect(() => {
    if (
      !catalogState.filteredFromItem ||
      catalogState.filteredFromItem.item_type !== 'folder.workflow' ||
      isMarketplaceCatalog
    ) {
      setAttachedActions({ uiActions: [], taskControlActions: [] });
      return;
    }
    const loadWorkflowActions = async () => {
      try {
        const attachedActions = await getAttachedActions(catalogState.filteredFromItem!);
        setAttachedActions(attachedActions);
      } catch (error) {
        console.error('Error loading workflow actions:', error);
        setAttachedActions({ uiActions: [], taskControlActions: [] });
      }
    };
    void loadWorkflowActions();
  }, [catalogState.filteredFromItem?.laui, catalogState.filteredFromItem?.item_type]);

  // Handle mouse down on resize handle
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setFolderSidebarState({ ...folderSidebarState, isResizing: true });
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

      <Box
        sx={{
          display: 'flex',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        <LeftSidebar />

        <Box sx={{ position: 'relative', display: 'flex' }}>
          <FolderSidebar />

          {/* Resize Handle */}
          {!folderSidebarState.isCollapsed && (
            <Box
              onMouseDown={handleMouseDown}
              sx={{
                width: '6px',
                cursor: 'col-resize',
                bgcolor: 'transparent',
                position: 'relative',
                flexShrink: 0,
                '&:hover': {
                  bgcolor: 'var(--accent)',
                },
                '&:hover::after': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  bottom: 0,
                  left: '-2px',
                  right: '-2px',
                  bgcolor: 'var(--accent)',
                  opacity: 0.3,
                },
              }}
            />
          )}
        </Box>

        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          {isLoading && (
            <Box
              sx={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: 'var(--bg-primary)',
                zIndex: 10,
              }}
            >
              <CircularProgress size={40} sx={{ color: 'var(--text-secondary)' }} />
            </Box>
          )}
          {itemNotFound ? (
            <Box
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 2,
                color: 'var(--text-secondary)',
              }}
            >
              <Box sx={{ fontSize: '48px', opacity: 0.5 }}>404</Box>
              <Box
                sx={{
                  fontSize: '18px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                }}
              >
                Item not found
              </Box>
              <Box sx={{ fontSize: '14px', opacity: 0.7 }}>
                The item you're looking for doesn't exist or may have been deleted.
              </Box>
            </Box>
          ) : (
            <>
              <ItemTabBar activeItemLaui={laui ?? null} />
              {mode === CatalogMode.DEFAULT &&
                !catalogState.selectedItem?.item_type?.startsWith('doc.') && (
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Breadcrumbs />
                    </Box>
                    {!isProjectItem && (
                      <Box sx={{ px: 1, flexShrink: 0 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => setDrillDownOpen((v) => !v)}
                          startIcon={
                            drillDownOpen ? (
                              <UnfoldLessIcon sx={{ fontSize: 14 }} />
                            ) : (
                              <UnfoldMoreIcon sx={{ fontSize: 14 }} />
                            )
                          }
                          sx={{
                            fontSize: '11px',
                            textTransform: 'none',
                            borderColor: 'var(--border)',
                            color: drillDownOpen ? 'var(--accent)' : 'var(--text-secondary)',
                            py: 0.25,
                            px: 1,
                            minWidth: 0,
                            lineHeight: 1,
                            '&:hover': {
                              borderColor: 'var(--accent)',
                              color: 'var(--accent)',
                            },
                          }}
                        >
                          Drill Down
                        </Button>
                      </Box>
                    )}
                  </Box>
                )}

              {mode === CatalogMode.DEFAULT && (
                <>
                  {/* Tabs Header — hidden for doc items; for non-project items hidden unless drillDownOpen */}
                  {!catalogState.selectedItem?.item_type?.startsWith('doc.') &&
                    (isProjectItem || drillDownOpen) && (
                      <Box
                        sx={{
                          borderBottom: 1,
                          borderColor: 'var(--border-color)',
                          bgcolor: 'var(--bg-secondary)',
                        }}
                      >
                        <Tabs
                          value={activeTab}
                          onChange={handleTabChange}
                          sx={{
                            minHeight: '32px',
                            '& .MuiTab-root': {
                              minHeight: '32px',
                              fontSize: '12px',
                              fontWeight: 400,
                              color: 'var(--text-secondary)',
                              textTransform: 'none',
                              '&.Mui-selected': {
                                color: 'var(--text-primary)',
                                fontWeight: 600,
                              },
                            },
                            '& .MuiTabs-indicator': {
                              backgroundColor: 'var(--text-primary)',
                              height: '2px',
                            },
                          }}
                        >
                          <Tab value="details" label="Item Details" />
                          {catalogState.selectedItem?.item_type?.includes('project') &&
                            ['own', 'edit'].includes(catalogState.selectedItem.permission) && (
                              <Tab value="scheduler" label="Scheduler" />
                            )}
                          <Tab value="parents" label="Parent Items" />
                          <Tab value="children" label="Child Items" />
                          {catalogState.openedFolder?.item_type?.includes('workflow') && (
                            <Tab value="graph" label="Graph View" />
                          )}
                        </Tabs>
                      </Box>
                    )}

                  {/* Tab Content */}
                  <Box
                    sx={{
                      flex: 1,
                      overflow: 'auto',
                    }}
                  >
                    {(catalogState.selectedItem?.item_type?.startsWith('doc.') ||
                      activeTab === 'details' ||
                      (activeTab === 'graph' &&
                        !catalogState.openedFolder?.item_type?.includes('workflow'))) && (
                      <ItemDetails />
                    )}

                    {activeTab === 'parents' &&
                      (catalogState.selectedItem || viewingItem || catalogState.openedFolder) && (
                        <ParentItemsComponent />
                      )}

                    {activeTab === 'children' &&
                      (catalogState.selectedItem || viewingItem || catalogState.openedFolder) && (
                        <ChildItemsComponent />
                      )}

                    {activeTab === 'graph' &&
                      catalogState.openedFolder?.item_type?.includes('workflow') && (
                        <WorkflowDiagram
                          tasks={catalogState.filteredItemsByType as any}
                          height={900}
                          workflowLaui={catalogState.openedFolder?.laui}
                        />
                      )}

                    {activeTab === 'scheduler' &&
                      catalogState.selectedItem?.item_type?.includes('project') && (
                        <SchedulerTab
                          projectLaui={catalogState.selectedItem.laui}
                          projectName={catalogState.selectedItem.name}
                          schedulerData={
                            (catalogState.selectedItem as any)?.folder_metadata || null
                          }
                          onRefresh={() => {
                            if (catalogState.selectedItem?.laui) {
                              void getCatalogItemById(catalogState.selectedItem.laui).then(
                                (updatedData) => {
                                  catalogState.setSelectedItem(updatedData as CatalogItem);
                                },
                              );
                            }
                          }}
                        />
                      )}
                  </Box>
                </>
              )}

              {mode === CatalogMode.USERS && <UsersGroupsTable />}
              {mode === CatalogMode.GROUPS && <GroupsView />}
            </>
          )}
        </Box>
      </Box>

      <LinkModal />
      <ShareModal />
      <SaveConfirmModal />
      <MarkdownModal />
      <ActionVariablesModal open={runActionModalData?.isOpen || false} />
      <DeleteModal />
      <RunTaskModal />
      <RestoreModal />
      <ImportModal />
    </Box>
  );
}
