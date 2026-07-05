/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Box, Tooltip, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';
import { Chip } from '@/components/ui';
import { getCoreVersion } from '@/config/version';
import { compatibilityMessage, isCoreCompatible } from '@/utils/semver';

import LAMarketplaceIcon from '../LAMarketplaceIcon/LAMarketplaceIcon';

interface MarketplaceCardProps {
  item: CatalogItem;
  onClick: (item: CatalogItem) => void;
}

export default function MarketplaceCard({ item, onClick }: Readonly<MarketplaceCardProps>) {
  const coreVersion = getCoreVersion();
  const incompatible = !isCoreCompatible(item.version_compatibility, coreVersion);
  const deprecated = !!item.version_details?.deprecated;
  const dimmed = incompatible || deprecated;
  const warningTip = incompatible
    ? (compatibilityMessage(item.version_compatibility, coreVersion) ?? 'Incompatible core version')
    : deprecated
      ? 'This item is deprecated'
      : '';
  const isOfficial = item.publisher === 'LeastAction';

  return (
    <Box
      onClick={() => onClick(item)}
      sx={{
        position: 'relative',
        p: 2,
        borderRadius: 2,
        border: '1px solid var(--border-color)',
        bgcolor: 'var(--bg-secondary)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        opacity: dimmed ? 0.6 : 1,
        transition: 'box-shadow 0.15s, border-color 0.15s',
        '&:hover': {
          boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
          borderColor: 'var(--accent)',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ width: 32, height: 32, flexShrink: 0, borderRadius: 1, overflow: 'hidden' }}>
          {item.image_url ? (
            <img
              src={item.image_url}
              width={32}
              height={32}
              style={{ objectFit: 'cover', display: 'block' }}
            />
          ) : (
            <LAMarketplaceIcon size={32} color="var(--accent)" seed={item.laui} />
          )}
        </Box>
        <Typography
          sx={{
            flex: 1,
            minWidth: 0,
            fontWeight: 600,
            fontSize: '13px',
            color: 'var(--text-primary)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {item.name}
        </Typography>
        {dimmed && (
          <Tooltip title={warningTip} placement="top">
            <WarningAmberIcon
              sx={{ fontSize: 14, color: incompatible ? 'error.main' : 'warning.main', flexShrink: 0 }}
            />
          </Tooltip>
        )}
      </Box>

      {item.description && (
        <Typography
          sx={{
            fontSize: '12px',
            color: 'var(--text-secondary)',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {item.description}
        </Typography>
      )}

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 'auto' }}>
        {item.item_type && <Chip label={item.item_type} variant="type" />}
        {item.category && <Chip label={item.category} variant="category" />}
        <Chip
          label={item.publisher ?? 'Unknown'}
          variant={isOfficial ? 'official' : 'publisher'}
          sx={{ fontStyle: item.publisher ? 'normal' : 'italic' }}
        />
        {item.tags?.slice(0, 3).map((tag) => <Chip key={tag} label={`#${tag}`} variant="tag" />)}
      </Box>
    </Box>
  );
}
