/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { InsertDriveFile as DocumentIcon } from '@mui/icons-material';

import { FONT_SIZES } from '@/constants';

interface TypeIconProps {
  type: string;
  iconCache: Record<
    string,
    {
      icon: React.ComponentType<any>;
      color: string;
    }
  >;
  large?: boolean;
}

const styles = {
  typeIcon: {
    fontSize: FONT_SIZES.ICON_SM,
    color: 'var(--text-secondary)',
  },
  typeIconDefault: {
    fontSize: FONT_SIZES.ICON_SM,
    color: 'var(--text-secondary)',
  },
};

export default function TypeIcon({ type, iconCache, large = false }: TypeIconProps) {
  const cached = iconCache[type];
  if (cached) {
    const IconComponent = cached.icon;
    return (
      <IconComponent
        sx={
          large
            ? { ...styles.typeIcon, color: cached.color, fontSize: FONT_SIZES.ICON_LG }
            : { ...styles.typeIcon, color: cached.color }
        }
      />
    );
  }
  return (
    <DocumentIcon
      sx={
        large
          ? { ...styles.typeIconDefault, fontSize: FONT_SIZES.ICON_LG }
          : { ...styles.typeIconDefault }
      }
    />
  );
}
