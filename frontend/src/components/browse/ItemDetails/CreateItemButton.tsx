/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// components/Browse/ItemDetails/CreateItemButton.tsx
import AddIcon from '@mui/icons-material/Add';
import { Button } from '@mui/material';

import { BUTTON_SIZES } from '@/constants';

type CreateItemButtonProps = {
  filterType: string;
  onClick: () => void;
  iconOnly?: boolean;
};

const styles = {
  button: {
    bgcolor: 'var(--text-primary)',
    color: 'var(--bg-secondary)',
    textTransform: 'none' as const,
    fontWeight: BUTTON_SIZES.FONT_WEIGHT,
    fontSize: BUTTON_SIZES.FONT_SIZE,
    height: BUTTON_SIZES.HEIGHT,
    padding: BUTTON_SIZES.PADDING,
    borderRadius: BUTTON_SIZES.BORDER_RADIUS,
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
    },
  },
  icon: {
    mr: 0.5,
    fontSize: BUTTON_SIZES.ICON_FONT_SIZE,
  },
};

export default function CreateItemButton({
  onClick,
  filterType,
  iconOnly = false,
}: CreateItemButtonProps) {
  const displayText = filterType.charAt(0).toUpperCase() + filterType.slice(1);

  return (
    <Button
      variant="contained"
      onClick={onClick}
      sx={styles.button}
      startIcon={<AddIcon sx={styles.icon} />}
      data-tour-target="create-item-button"
    >
      {iconOnly ? '' : `Add ${displayText}`}
    </Button>
  );
}
