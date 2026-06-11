/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import DescriptionIcon from '@mui/icons-material/Description';
import { Box, CircularProgress, Typography } from '@mui/material';

import { ItemStatusChips } from '@/components/ui';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { isDocItem } from '@/utils/docsTree';

import { FONT_SIZES, FONT_WEIGHTS } from '../../../constants';
import { getCatalogItemById } from '../../../services/catalog.service';
import type { FullItemData } from '../types';
import EmptyState from './EmptyState';

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
    alignItems: 'flex-start',
    gap: 2,
    mb: 2,
  },
  itemIcon: {
    fontSize: 40,
    color: 'var(--accent-primary)',
    mt: 0.5,
  },
  title: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.SEMIBOLD,
    mb: 0.75,
  },
  jsonContainer: {
    bgcolor: 'var(--bg-secondary)',
    borderRadius: 1,
    p: 2,
    overflow: 'auto',
    maxHeight: '400px',
    fontFamily: 'monospace',
    fontSize: FONT_SIZES.XS,
    border: '1px solid var(--border-primary)',
  },
  jsonText: {
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    margin: 0,
  },
};

export default function ItemView() {
  const { catalogType } = useGlobal();
  const { catalogState } = useCatalog();

  const { selectedItem } = catalogState;
  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const [fullItemData, setFullItemData] = useState<FullItemData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchItemData = async () => {
      if (!selectedItem?.laui) {
        setFullItemData(null);
        return;
      }

      // Doc items are in-memory only (no ObjectId) — never hit the catalog API for them.
      if (isDocItem(selectedItem.laui)) {
        setFullItemData(null);
        return;
      }

      setLoading(true);
      try {
        const data = await getCatalogItemById(selectedItem.laui, isMarketplaceCatalog);
        setFullItemData(data);
      } catch (err) {
        console.error('Error fetching item data:', err);
      } finally {
        setLoading(false);
      }
    };

    void fetchItemData();
  }, [selectedItem?.laui]);

  if (!selectedItem) {
    return (
      <Box sx={styles.container}>
        <Box sx={styles.content}>
          <EmptyState message="Select an item to view its details" />
        </Box>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={styles.container}>
        <Box sx={styles.content}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: '200px',
            }}
          >
            <CircularProgress />
          </Box>
        </Box>
      </Box>
    );
  }

  if (!fullItemData) {
    return (
      <Box sx={styles.container}>
        <Box sx={styles.content}>
          <EmptyState message="No item data available" />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={styles.container}>
      <Box sx={styles.content}>
        <Box sx={styles.header}>
          <DescriptionIcon sx={styles.itemIcon} />
          <Box sx={{ flex: 1 }}>
            <Typography variant="h6" sx={styles.title}>
              {fullItemData.name || 'Unnamed'}
            </Typography>
            <ItemStatusChips
              itemType={fullItemData.item_type}
              marketplaceLaui={fullItemData.marketplace_laui}
              isPublished={fullItemData.is_published}
              hasUnpublishedChanges={fullItemData.has_unpublished_changes}
            />
          </Box>
        </Box>

        <Box sx={styles.jsonContainer}>
          <Typography component="pre" sx={styles.jsonText}>
            {JSON.stringify(fullItemData, null, 2)}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
