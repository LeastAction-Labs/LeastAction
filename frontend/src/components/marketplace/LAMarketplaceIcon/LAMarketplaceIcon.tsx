/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Tooltip } from '@mui/material';

import { physicsIcons } from '@/utils/physicsIcons';

interface LAMarketplaceIconProps {
  size?: number;
  color?: string;
  /** Seed string (e.g. item laui) for deterministic icon selection */
  seed?: string;
}

/** Simple hash: sum of char codes mod array length */
function seedToIndex(seed: string, length: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash + seed.charCodeAt(i)) % length;
  }
  return hash;
}

/**
 * Shows a randomly-but-deterministically selected physics icon from physicsIcons.tsx.
 * Displayed when an item has no image_url. Tooltip explains what the icon is
 * and that it's a placeholder.
 */
export default function LAMarketplaceIcon({
  size = 40,
  color = 'var(--accent)',
  seed = '',
}: LAMarketplaceIconProps) {
  const icon = physicsIcons[seedToIndex(seed, physicsIcons.length)];

  const tooltipContent = (
    <span>
      <strong>{icon.name}</strong>
      <br />
      {icon.description}
      <br />
      <em style={{ opacity: 0.7, fontSize: '11px' }}>No image URL set for this item</em>
    </span>
  );

  return (
    <Tooltip title={tooltipContent} placement="right" arrow>
      <div
        style={{
          width: size,
          height: size,
          color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'default',
          flexShrink: 0,
        }}
      >
        {icon.svg}
      </div>
    </Tooltip>
  );
}
