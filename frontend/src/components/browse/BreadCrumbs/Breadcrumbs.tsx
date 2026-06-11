/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import { Box, Link, Breadcrumbs as MUIBreadcrumbs, Tooltip, Typography } from '@mui/material';

import TypeIcon from '@/components/ui/TypeIcon';
import { FONT_SIZES, TRANSITIONS } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { useBreadcrumbHandlers } from '@/screens/Browse/handlers';
import { useCatalogTree } from '@/screens/Browse/hooks';
import { getItemTypeVisualConfig } from '@/services/schema.service';
import { getIconComponent } from '@/utils/iconMapping';

import type { CatalogItem } from '../types';

// Styles //
const styles = {
  container: {
    px: 2,
    py: 1,
    bgcolor: 'var(--bg-primary)',
    borderTop: 1,
    borderColor: 'var(--border)',
  },
  separator: {
    color: 'var(--text-secondary)',
    mx: 0.5,
  },
  breadcrumbs: {
    color: 'var(--text-primary)',
    '& .MuiBreadcrumbs-ol': { alignItems: 'center' },
  },
  baseItem: {
    color: 'var(--text-primary)',
    opacity: 0.9,
    maxWidth: 220,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 0.5,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    verticalAlign: 'middle',
    transition: 'opacity 0.2s ease',
  },
  icon: {
    fontSize: FONT_SIZES.ICON_MD,
    color: 'var(--text-secondary)',
    flexShrink: 0,
  },
  linkItem: {
    px: 0.5,
    textAlign: 'left',
    outline: 0,
    borderRadius: 0.5,
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      textDecoration: 'underline',
      opacity: 1,
      color: 'var(--accent)',
    },
    '&:focus-visible': {
      textDecoration: 'underline',
      opacity: 1,
      color: 'var(--accent)',
    },
  },
};

export default function Breadcrumbs() {
  const { breadcrumbPath } = useCatalogTree();
  const path = breadcrumbPath;
  const { catalogState, editorState } = useCatalog();
  const { activeFilterType, selectedItem, isItemFromTable, lastFilterType, isBreadcrumbLocked } =
    catalogState;
  const { formMode, viewingItem, editingItem, isEditorActive } = editorState;

  const { handleBreadcrumbSelect } = useBreadcrumbHandlers();

  const filterType =
    activeFilterType ||
    (formMode === 'view' && viewingItem ? viewingItem.item_type : null) ||
    (isItemFromTable ? lastFilterType : null);

  const handleClick = (id: string, isLast: boolean) => {
    if (isLast) return;
    void handleBreadcrumbSelect(id);
  };

  const breadcrumbItems = useMemo(() => {
    const items: CatalogItem[] = [...path];

    if (isBreadcrumbLocked) return items;

    if (isEditorActive) {
      const typeLabel = filterType ?? selectedItem?.item_type ?? '';
      const viewingName = viewingItem?.name ?? typeLabel;
      const itemType = viewingItem?.item_type ?? editingItem?.item_type ?? 'form';
      items.push({
        laui: `form-${formMode}`,
        name:
          formMode === 'create'
            ? `Add new ${typeLabel}`
            : formMode === 'edit'
              ? `Edit ${viewingName}`
              : `View ${viewingName}`,
        item_type: itemType,
      } as CatalogItem);
    }

    return items;
  }, [path, filterType, selectedItem, formMode, isBreadcrumbLocked, editorState.isEditorActive]);

  const [iconCache, setIconCache] = useState<
    Record<string, { icon: React.ComponentType<any>; color: string }>
  >({});

  // Load visual config for item types
  useEffect(() => {
    const loadVisualConfigs = async () => {
      const types = [...new Set(breadcrumbItems.map((item) => item.item_type).filter(Boolean))];
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

    void loadVisualConfigs();
  }, [breadcrumbItems]);

  return (
    <Box sx={styles.container}>
      <MUIBreadcrumbs
        aria-label="breadcrumb"
        separator={<Typography sx={styles.separator}>{'›'}</Typography>}
        sx={styles.breadcrumbs}
      >
        {breadcrumbItems.length === 0 ? (
          <Typography variant="body2" sx={{ ...styles.baseItem, color: 'var(--text-primary)' }}>
            Root
          </Typography>
        ) : (
          breadcrumbItems.map((item, index) => {
            const isLast = index === breadcrumbItems.length - 1;
            const label = item.name || 'Item';

            if (isLast) {
              return (
                <Tooltip key={item.laui} title={label} arrow>
                  <Typography
                    variant="body2"
                    component="span"
                    sx={styles.baseItem}
                    aria-current="page"
                  >
                    <TypeIcon type={item.item_type} iconCache={iconCache} large={true} />
                    {label}
                  </Typography>
                </Tooltip>
              );
            }

            return (
              <Tooltip key={item.laui} title={label} arrow>
                <Link
                  underline="none"
                  color="inherit"
                  component="button"
                  role="link"
                  tabIndex={0}
                  variant="body2"
                  onClick={() => handleClick(item.laui, isLast)}
                  sx={{ ...styles.baseItem, ...styles.linkItem }}
                >
                  <TypeIcon type={item.item_type} iconCache={iconCache} large={true} />
                  {label}
                </Link>
              </Tooltip>
            );
          })
        )}
      </MUIBreadcrumbs>
    </Box>
  );
}
