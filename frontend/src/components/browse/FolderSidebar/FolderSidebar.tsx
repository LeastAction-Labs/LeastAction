/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactElement } from 'react';
import { useEffect, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import { Box, Typography } from '@mui/material';

import CreateProjectModal from '@/components/browse/modals/CreateProjectModal';
import { FONT_SIZES, FONT_WEIGHTS, LETTER_SPACING, TRANSITIONS } from '@/constants';
import { CatalogMode, useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { useSidebarHandlers } from '@/screens/Browse/handlers';
import { getItemTypeVisualConfig } from '@/services/schema.service';
import { getDocsTree } from '@/utils/docsTree';
import { getIconComponent } from '@/utils/iconMapping';

import type { CatalogNode } from '../types';
import CatalogTreeNode from './CatalogTreeNode';

const styles = {
  container: (_isCollapsed: boolean) => ({
    flexShrink: 0,
    width: '100%',
    height: '100%',
    bgcolor: 'var(--bg-primary)',
    borderRight: 1,
    borderTop: 1,
    borderColor: 'var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  }),
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 1,
    px: 2,
    pb: 1,
    pt: 1,
    flexShrink: 0,
    alignItems: 'center',
    mb: 1,
    position: 'relative',
    zIndex: 10,
  },
  headerTitle: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.MEDIUM,
    fontSize: FONT_SIZES.BASE,
    letterSpacing: LETTER_SPACING.TIGHT,
  },
  moreOptionsButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    border: 'none',
    bgcolor: 'transparent',
    color: 'var(--text-secondary)',
    transition: `color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      color: 'var(--text-primary)',
    },
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    overflowX: 'hidden',
    px: 2,
    pb: 2,
    '& > * + *': { mt: 1 },
  },
  actionIcon: {
    color: 'var(--text-primary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      color: 'var(--accent)',
      bgcolor: 'var(--bg-tertiary)',
    },
  },
};

export interface FolderSidebarStateData {
  isCollapsed: boolean;
  width: number;
  isResizing: boolean;
}

// helper functions

// Collect all unique supported types from the tree
const collectSupportedTypes = (nodes: CatalogNode[]): string[] => {
  const types = new Set<string>();
  const traverse = (node: CatalogNode) => {
    const supportedTypes = (node.item as any).supported_types || [];
    supportedTypes.forEach((type: string) => {
      if (!type.toLowerCase().startsWith('folder.')) {
        types.add(type);
      }
    });
    if (node.children) {
      node.children.forEach(traverse);
    }
  };
  nodes.forEach(traverse);
  return Array.from(types);
};

export default function FolderSidebar() {
  const { handleSelectGroups, handleSelectUsers } = useSidebarHandlers();

  const { catalogType, folderSidebarState, setFolderSidebarState } = useGlobal();
  const { catalogState, mode } = useCatalog();
  const { userAuthenticated: userAuthenticatedToMarketplace } = useMarketplace();

  const { items, isLoading, error } = catalogState;

  const { isCollapsed } = folderSidebarState;

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  // Only users with own/edit on the account folder can create projects
  const accountPermission =
    items.length > 0 && items[0].item.item_type === 'folder.account'
      ? items[0].item.permission
      : null;
  const canCreateProject =
    !isMarketplaceCatalog && ['own', 'edit'].includes(accountPermission ?? '');

  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const INITIAL_PROJECTS_VISIBLE = 10;
  const [visibleProjectCount, setVisibleProjectCount] = useState(INITIAL_PROJECTS_VISIBLE);

  // State for caching icon and color configurations
  const [iconCache, setIconCache] = useState<
    Record<string, { icon: React.ComponentType<any>; color: string }>
  >({});

  useEffect(() => {
    const loadVisualConfigs = async () => {
      const types = collectSupportedTypes(items);
      const configs: Record<string, { icon: React.ComponentType<any>; color: string }> = {};

      for (const type of types) {
        if (type) {
          const visualConfig = await getItemTypeVisualConfig(type);
          if (visualConfig) {
            configs[type] = {
              icon: getIconComponent(visualConfig.icon),
              color: visualConfig.color,
            };
          }
        }
      }

      setIconCache(configs);
    };

    if (items.length > 0) {
      void loadVisualConfigs();
    }
  }, [items]);

  useEffect(() => {
    let newWidth = folderSidebarState.width;
    const handleMouseMove = (e: MouseEvent) => {
      if (!folderSidebarState.isResizing) return;
      const currWidth = e.clientX - 60; // 60px is the LeftSidebar width
      const minWidth = 200;
      const maxWidth = 600;
      if (currWidth >= minWidth && currWidth <= maxWidth) {
        newWidth = currWidth;
        setFolderSidebarState({ ...folderSidebarState, width: newWidth });
      }
    };
    const handleMouseUp = () => {
      setFolderSidebarState({ ...folderSidebarState, width: newWidth, isResizing: false });
    };
    if (folderSidebarState.isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [folderSidebarState.isResizing]);

  const renderTreeNode = (
    node: CatalogNode,
    depth: number = 0,
    deletePermission: boolean = false,
    restoreAble: boolean = false,
    parentLaui?: string,
  ): ReactElement => {
    deletePermission = deletePermission || node.item.permission === 'own';
    const childDeletePermission =
      deletePermission || ['edit', 'own'].includes(node.item.permission);

    const childRestoreAble = restoreAble || node.item.item_type === 'folder.trash';

    return (
      <CatalogTreeNode
        key={node.item.laui}
        node={node}
        depth={depth}
        renderChild={(child, childDepth) =>
          renderTreeNode(child, childDepth, childDeletePermission, childRestoreAble, node.item.laui)
        }
        iconCache={iconCache}
        deletePermission={deletePermission}
        restoreAble={restoreAble}
        parentLaui={parentLaui}
      />
    );
  };

  const loadingStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    p: 3,
    color: 'var(--text-secondary)',
  };

  const errorStyles = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    p: 3,
    color: 'var(--error)',
  };

  // If the first item is a folder.account (root account folder), use its children as root nodes
  // Otherwise, use the items as-is
  let displayNodes = items;
  const accountLaui =
    items.length > 0 && items[0].item.item_type === 'folder.account'
      ? items[0].item.laui
      : undefined;
  if (items.length > 0 && items[0].item.item_type === 'folder.account') {
    displayNodes = items[0].children || [];
  }

  let rootNodes = [];
  let hasMoreProjects = false;
  let trailingNodes: CatalogNode[] = [];

  if (isMarketplaceCatalog) {
    rootNodes = displayNodes;
  } else {
    const ownedItems = displayNodes.filter((itemNode) => itemNode.item.permission === 'own');
    const sharedItems = displayNodes.filter((itemNode) => itemNode.item.permission !== 'own');
    const sharedWithMeNode: CatalogNode = {
      item: { name: 'Shared With Me', laui: 'shared', item_type: '', permission: 'view' },
      children: sharedItems,
      parents: [],
    };

    hasMoreProjects = ownedItems.length > visibleProjectCount;
    const visibleOwnedItems = ownedItems.slice(0, visibleProjectCount);

    rootNodes = [getDocsTree(), ...visibleOwnedItems];
    if (sharedWithMeNode.children.length !== 0) trailingNodes = [sharedWithMeNode];
  }

  const shouldShowError = !!error && !error.toLowerCase().includes('deep link');

  return (
    <Box
      sx={{
        width: folderSidebarState.isCollapsed ? 0 : `${folderSidebarState.width}px`,
        flexShrink: 0,
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      <Box sx={styles.container(isCollapsed)}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 1,
            py: 0.5,
            borderBottom: '1px solid var(--border)',
          }}
        >
          <Typography
            sx={{
              fontSize: FONT_SIZES.BASE,
              fontWeight: FONT_WEIGHTS.MEDIUM,
              color: 'var(--text-primary)',
              px: 0.5,
            }}
          >
            Browse
          </Typography>
          {canCreateProject && (
            <Box
              onClick={() => setCreateProjectOpen(true)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                cursor: 'pointer',
                color: 'var(--text-secondary)',
                fontSize: FONT_SIZES.SM,
                px: 0.75,
                py: 0.25,
                borderRadius: '4px',
                transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
                '&:hover': {
                  color: 'var(--text-primary)',
                  bgcolor: 'var(--bg-tertiary)',
                },
              }}
            >
              <AddIcon sx={{ fontSize: 14 }} />
              <Typography sx={{ fontSize: FONT_SIZES.SM, fontWeight: FONT_WEIGHTS.MEDIUM }}>
                New Project
              </Typography>
            </Box>
          )}
        </Box>
        {isLoading && (
          <Box sx={loadingStyles}>
            <Typography variant="body2">Loading items…</Typography>
          </Box>
        )}
        {shouldShowError && (
          <Box sx={errorStyles}>
            <Typography variant="body2">{error}</Typography>
          </Box>
        )}
        {!isLoading && !shouldShowError && (
          <>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                py: 1,
                overflow: 'hidden',
              }}
            >
              <Box sx={styles.content}>
                {rootNodes.length !== 0 || trailingNodes.length !== 0 ? (
                  <Box sx={{ '& > * + *': { mt: 1 } }}>
                    {rootNodes.map((itemNode) =>
                      renderTreeNode(itemNode, 0, false, false, accountLaui),
                    )}
                    {hasMoreProjects && (
                      <Box
                        sx={{ mt: 0.5, px: 1 }}
                        onClick={() => setVisibleProjectCount((c) => c + INITIAL_PROJECTS_VISIBLE)}
                      >
                        <Typography
                          variant="caption"
                          sx={{
                            color: 'var(--accent)',
                            cursor: 'pointer',
                            '&:hover': { textDecoration: 'underline' },
                          }}
                        >
                          Load more...
                        </Typography>
                      </Box>
                    )}
                    {trailingNodes.map((itemNode) =>
                      renderTreeNode(itemNode, 0, false, false, accountLaui),
                    )}
                  </Box>
                ) : (
                  <Typography variant="body2">You dont have access to any items</Typography>
                )}
              </Box>
            </Box>
            {!isMarketplaceCatalog && (
              <>
                <Box
                  sx={{
                    px: 2,
                    py: 1.5,
                    cursor: 'pointer',
                    borderTop: '1px solid var(--border)',
                    bgcolor: mode === CatalogMode.USERS ? 'var(--bg-tertiary)' : 'transparent',
                    transition: `background-color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
                    '&:hover': {
                      bgcolor: 'var(--bg-tertiary)',
                    },
                  }}
                  onClick={handleSelectUsers}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: mode === CatalogMode.USERS ? 'var(--accent)' : 'var(--text-primary)',
                      fontWeight:
                        mode === CatalogMode.USERS ? FONT_WEIGHTS.MEDIUM : FONT_WEIGHTS.NORMAL,
                      fontSize: FONT_SIZES.BASE,
                    }}
                  >
                    Manage Users and Groups Access
                  </Typography>
                </Box>
                <Box
                  sx={{
                    px: 2,
                    py: 1.5,
                    cursor: 'pointer',
                    borderTop: '1px solid var(--border)',
                    bgcolor: mode === CatalogMode.GROUPS ? 'var(--bg-tertiary)' : 'transparent',
                    transition: `background-color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
                    '&:hover': {
                      bgcolor: 'var(--bg-tertiary)',
                    },
                  }}
                  onClick={handleSelectGroups}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      color: mode === CatalogMode.GROUPS ? 'var(--accent)' : 'var(--text-primary)',
                      fontWeight:
                        mode === CatalogMode.GROUPS ? FONT_WEIGHTS.MEDIUM : FONT_WEIGHTS.NORMAL,
                      fontSize: FONT_SIZES.BASE,
                    }}
                  >
                    Manage Groups
                  </Typography>
                </Box>
              </>
            )}
            {isMarketplaceCatalog && (
              <>
                {userAuthenticatedToMarketplace && (
                  <Box
                    sx={{
                      px: 2,
                      py: 1.5,
                      cursor: 'pointer',
                      borderTop: '1px solid var(--border)',
                      bgcolor: 'transparent',
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        color: 'var(--text-primary)',
                        fontWeight: FONT_WEIGHTS.MEDIUM,
                        fontSize: FONT_SIZES.BASE,
                      }}
                    >
                      Logged in to marketplace
                    </Typography>
                  </Box>
                )}
              </>
            )}
          </>
        )}
      </Box>

      <CreateProjectModal open={createProjectOpen} onClose={() => setCreateProjectOpen(false)} />
    </Box>
  );
}
