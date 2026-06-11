/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box } from '@mui/material';

import Chip from './Chip';

interface ItemStatusChipsProps {
  itemType?: string;
  marketplaceLaui?: string;
  isPublished?: boolean;
  hasUnpublishedChanges?: boolean;
}

export default function ItemStatusChips({
  itemType,
  marketplaceLaui,
  isPublished,
  hasUnpublishedChanges,
}: ItemStatusChipsProps) {
  const isFromMarketplace = !!marketplaceLaui;
  const mpHref = isFromMarketplace
    ? `/marketplace?laui=${encodeURIComponent(marketplaceLaui)}`
    : undefined;

  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
      {itemType && <Chip label={itemType} variant="type" />}
      {isFromMarketplace ? (
        <Chip
          label="From Marketplace"
          variant="mp"
          clickable
          onClick={() => window.open(mpHref, '_self')}
          tooltip="View source listing in Marketplace"
        />
      ) : (
        <Chip
          label="Native"
          variant="native"
          tooltip="Item created locally, not from Marketplace"
        />
      )}
      {isPublished === true && !hasUnpublishedChanges && (
        <Chip label="Published" variant="published" tooltip="Published to Marketplace" />
      )}
      {isPublished === true && hasUnpublishedChanges && (
        <Chip
          label="Pending changes"
          variant="draft"
          tooltip="Local changes not yet published to Marketplace"
        />
      )}
      {isPublished === false && (
        <Chip label="Draft" variant="draft" tooltip="Not yet published to Marketplace" />
      )}
    </Box>
  );
}
