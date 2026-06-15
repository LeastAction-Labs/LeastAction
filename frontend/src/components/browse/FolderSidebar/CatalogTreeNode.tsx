/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactElement } from 'react';
import React from 'react';

import {
  ChevronRight,
  Delete as DeleteIcon,
  Description as DescriptionIcon,
  Refresh as RefreshIcon,
  Restore as RestoreIcon,
  Share as ShareIcon,
} from '@mui/icons-material';
import { Box, IconButton, Typography } from '@mui/material';

import { ItemTypeTooltip } from '@/components/ui';
import { FONT_SIZES, FONT_WEIGHTS, SPACING, TRANSITIONS } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useSidebarHandlers } from '@/screens/Browse/handlers';
import { useRefreshHandlers } from '@/screens/Browse/handlers/refreshHandlers';

import type { CatalogItem, CatalogNode } from '../types';

// Component-specific styles
const styles = {
  itemBar: (depth: number, isSelected: boolean) => ({
    bgcolor:
      depth === 0 ? 'var(--bg-depth-0)' : isSelected ? 'var(--bg-selected)' : 'var(--bg-primary)',
    borderRadius: 1,
    display: 'flex',
    alignItems: 'center',
    px: 0.25,
    py: 0.25,
    cursor: 'pointer',
    ml: depth > 0 ? `${depth * SPACING.INDENT_PER_LEVEL}rem` : 0,
    transition: `background-color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: depth === 0 ? 'var(--bg-depth-0)' : 'var(--bg-selected)',
    },
  }),
  expandButton: {
    color: 'var(--text-primary)',
    cursor: 'pointer',
    transition: `opacity ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: 'var(--bg-tertiary)',
    },
  },
  expandButtonDisabled: {
    color: 'var(--text-primary)',
    cursor: 'default',
    opacity: 0.5,
    transition: `opacity ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
  },
  chevronIcon: {
    fontSize: 15,
    color: 'var(--text-primary)',
    transform: 'rotate(0deg)',
    transition: `transform ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
  },
  chevronIconExpanded: {
    fontSize: 15,
    color: 'var(--text-primary)',
    transform: 'rotate(90deg)',
    transition: `transform ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
  },
  itemName: (depth: number) => ({
    flex: 1,
    color: 'var(--text-primary)',
    fontWeight: depth === 0 ? FONT_WEIGHTS.MEDIUM : FONT_WEIGHTS.NORMAL,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  }),
  actionIcon: {
    color: 'var(--text-primary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      color: 'var(--accent)',
      bgcolor: 'var(--bg-tertiary)',
    },
  },
  typeIcon: {
    fontSize: FONT_SIZES.ICON_XS,
    color: 'var(--text-secondary)',
  },
  typeIconDefault: {
    fontSize: FONT_SIZES.ICON_SM,
    color: 'var(--text-secondary)',
  },
  supportedTypeItem: (depth: number, isSelected: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    px: 2,
    py: 1,
    ml: `${(depth + 1) * SPACING.INDENT_PER_LEVEL}rem`,
    borderRadius: 1,
    bgcolor: isSelected ? 'var(--bg-selected)' : 'var(--bg-primary)',
    cursor: 'pointer',
    transition: `background-color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: 'var(--bg-selected)',
    },
    gap: 1,
  }),
  selectedTypeName: {
    color: 'var(--accent)',
    fontWeight: FONT_WEIGHTS.MEDIUM,
  },
  typeName: {
    color: 'var(--text-primary)',
  },
  loadingText: {
    color: 'var(--text-secondary)',
  },
};

type CatalogTreeNodeProps = {
  node: CatalogNode;
  depth: number;
  renderChild?: (child: CatalogNode, childDepth: number) => ReactElement;
  openSupportedType?: string | null; // NEW: Track which supported type is open for this folder
  iconCache?: Record<string, { icon: React.ComponentType<any>; color: string }>; // ADDED: Icon/color cache from parent
  deletePermission: boolean;
  restoreAble: boolean;
  parentLaui?: string;
};

function areChildrenLoaded(node: CatalogNode, loadedChildren: Set<string>) {
  const isVirtualNode = node.item.item_type === '';
  const isMonitorFolder = node.item.laui.startsWith('monitor-');
  const isDocItem = node.item.item_type?.startsWith('doc.');
  return isVirtualNode || isMonitorFolder || isDocItem ? true : loadedChildren.has(node.item.laui);
}

export default function CatalogTreeNode({
  node,
  depth,
  renderChild,
  openSupportedType: _openSupportedType = null, // NEW: Pass down which supported type is open
  iconCache: _iconCache = {}, // ADDED: Icon/color cache from parent,
  deletePermission,
  restoreAble,
  parentLaui,
}: CatalogTreeNodeProps) {
  const { catalogType } = useGlobal();
  const { catalogState, setRestoreModalState } = useCatalog();
  const { expandedItems, selectedItem, loadingChildren, loadedChildren, childrenPagination } =
    catalogState;
  const isExpanded = expandedItems.has(node.item.laui);
  const isSelected = selectedItem?.laui === node.item.laui;
  const isLoadingChild = loadingChildren.has(node.item.laui);
  const childrenLoaded = areChildrenLoaded(node, loadedChildren);
  const { handleSelectItem, handleToggleExpand, loadMoreChildren } = useSidebarHandlers();
  const nodePagination = childrenPagination[node.item.laui];
  const hasMore = nodePagination?.has_next === true;
  const { handleRefreshItem } = useRefreshHandlers();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const hasChildren = node.children && node.children.length > 0;
  const itemName = node.item?.data?.name || node.item?.name || 'Unnamed';
  const supportedTypes: string[] =
    (node.item as unknown as { supported_types?: string[] }).supported_types || [];
  const nonFolderSupportedTypes = supportedTypes.filter(
    (t: string) => !t.toLowerCase().startsWith('folder.'),
  );

  const isDocFile = node.item.item_type === 'doc.file';

  // Can expand if it has children, or if it has non-folder supported types (for collapsing), or if it's a monitor folder
  const canExpand = !childrenLoaded || hasChildren || nonFolderSupportedTypes.length > 0;

  const isRemoveable =
    !['folder.trash', 'folder.users', 'doc.folder', 'doc.file'].includes(node.item.item_type) &&
    deletePermission;

  const isShareAble =
    !['folder.trash', 'folder.users'].includes(node.item.item_type) &&
    ['edit', 'own'].includes(node.item.permission);

  const { setDeleteModalState, setShareModalState } = useCatalog();

  const handleDivClick = () => {
    void handleSelectItem(node.item.laui);
    if (canExpand) void handleToggleExpand(node.item.laui, node.item.permission);
  };

  const handleDelete = () => {
    setDeleteModalState({
      isOpen: true,
      itemLaui: node.item.laui,
      itemName: node.item.name,
      parentLaui: parentLaui,
    });
  };

  const handleShare = (item: CatalogItem) => {
    setShareModalState({ isOpen: true, item: item });
  };

  const handleRestore = (item: CatalogItem) => {
    setRestoreModalState({ isOpen: true, item: item });
  };

  const handleLoadMore = async (e: React.MouseEvent) => {
    e.stopPropagation();
    await loadMoreChildren(node.item.laui, node.item.permission);
  };

  return (
    <Box>
      {/* Item Bar */}
      <Box sx={styles.itemBar(depth, isSelected)} onClick={handleDivClick}>
        {/* Expand Arrow */}
        {!isDocFile && (
          <IconButton
            size="small"
            sx={canExpand ? styles.expandButton : styles.expandButtonDisabled}
            disabled={!canExpand}
          >
            {isLoadingChild ? (
              <Typography variant="caption" sx={styles.loadingText}>
                ...
              </Typography>
            ) : (
              <ChevronRight sx={isExpanded ? styles.chevronIconExpanded : styles.chevronIcon} />
            )}
          </IconButton>
        )}
        {depth === 0 && (
          <Box sx={{ display: 'flex', gap: 0.1, alignItems: 'center' }}>
            <Typography variant="body2" sx={styles.itemName(depth)}>
              {/* REMOVED: Project: label */}
            </Typography>
          </Box>
        )}
        {/* Doc file icon */}
        {isDocFile && (
          <DescriptionIcon
            sx={{
              fontSize: 13,
              color: 'var(--text-secondary)',
              mr: 0.5,
              flexShrink: 0,
            }}
          />
        )}
        {/* Item Name */}
        <Typography variant="body2" sx={styles.itemName(depth)}>
          {itemName}
        </Typography>
        <ItemTypeTooltip itemType={node.item.item_type} />

        {/* Root-level Action Icons */}
        {depth === 0 ? (
          <Box sx={{ display: 'flex', gap: 0.1, alignItems: 'center' }}>
            <IconButton
              size="small"
              sx={styles.actionIcon}
              onClick={(e) => {
                e.stopPropagation();
                void handleRefreshItem(node.item.laui, node.item.permission);
              }}
            >
              <RefreshIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
            </IconButton>

            {isShareAble && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleShare(node.item);
                }}
              >
                <ShareIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}

            {isRemoveable && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete();
                }}
              >
                <DeleteIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}
            {restoreAble && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleRestore(node.item);
                }}
              >
                <RestoreIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}
          </Box>
        ) : (
          <Box sx={{ display: 'flex', gap: 0.1, alignItems: 'center' }}>
            <IconButton
              size="small"
              sx={styles.actionIcon}
              onClick={(e) => {
                e.stopPropagation();
                void handleRefreshItem(node.item.laui, node.item.permission);
              }}
            >
              <RefreshIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
            </IconButton>

            {!isMarketplaceCatalog && isShareAble && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleShare(node.item);
                  // TODO: Implement add action
                }}
              >
                <ShareIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}
            {isRemoveable && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete();
                }}
              >
                <DeleteIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}
            {restoreAble && (
              <IconButton
                size="small"
                sx={styles.actionIcon}
                onClick={(e) => {
                  e.stopPropagation();
                  handleRestore(node.item);
                }}
              >
                <RestoreIcon sx={{ fontSize: FONT_SIZES.ICON_MD }} />
              </IconButton>
            )}
          </Box>
        )}
      </Box>
      {/* Children */}
      {isExpanded && (
        <Box sx={{ mt: 0.5, '& > * + *': { mt: 0.25 } }}>
          {isLoadingChild ? (
            <Typography variant="caption" sx={{ ...styles.loadingText, ml: 8, px: 1.5, py: 0.75 }}>
              Loading...
            </Typography>
          ) : (
            <>
              {hasChildren &&
                renderChild &&
                node.children.map((child) => renderChild(child, depth + 1))}

              {hasMore && !isLoadingChild && (
                <Box
                  sx={{
                    ml: `${(depth + 1) * SPACING.INDENT_PER_LEVEL}rem`,
                    mt: 0.5,
                    px: 1,
                  }}
                  onClick={(e) => void handleLoadMore(e)}
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
            </>
          )}
        </Box>
      )}
    </Box>
  );
}
