/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import { Button, Menu, MenuItem } from '@mui/material';

import { BUTTON_SIZES, FONT_SIZES } from '@/constants';

type AddItemDropdownProps = {
  types: string[];
  onSelect: (type: string) => void;
};

function getDisplayName(type: string): string {
  return type
    .split('.')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function deduplicateTypes(types: string[]): string[] {
  const hasFolderSubtype = types.some((t) => t.startsWith('folder.') || t === 'folder');
  const nonFolderTypes = types.filter((t) => !t.startsWith('folder.') && t !== 'folder');
  return hasFolderSubtype ? ['folder', ...nonFolderTypes] : nonFolderTypes;
}

const buttonStyle = {
  bgcolor: 'var(--text-primary)',
  color: 'var(--bg-secondary)',
  textTransform: 'none' as const,
  fontWeight: BUTTON_SIZES.FONT_WEIGHT,
  fontSize: BUTTON_SIZES.FONT_SIZE,
  height: BUTTON_SIZES.HEIGHT,
  padding: BUTTON_SIZES.PADDING,
  borderRadius: BUTTON_SIZES.BORDER_RADIUS,
  minWidth: 0,
  '& .MuiButton-endIcon': { ml: 0.25 },
  '&:hover': {
    bgcolor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
  },
};

const menuPaperStyle = {
  bgcolor: 'var(--bg-secondary)',
  border: '1px solid var(--border)',
  boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
  mt: 0.5,
};

const menuItemStyle = {
  fontSize: FONT_SIZES.SM,
  color: 'var(--text-primary)',
  py: 0.75,
  px: 1.5,
  display: 'flex',
  alignItems: 'center',
  gap: 0.75,
  '&:hover': { bgcolor: 'var(--bg-hover)' },
};

export default function AddItemDropdown({ types, onSelect }: AddItemDropdownProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleOpen = (e: React.MouseEvent<HTMLElement>) => {
    e.stopPropagation();
    setAnchorEl(e.currentTarget);
  };

  const handleClose = () => setAnchorEl(null);

  const handleSelect = (type: string) => {
    handleClose();
    onSelect(type);
  };

  const dedupedTypes = deduplicateTypes(types);

  if (dedupedTypes.length === 0) return null;

  if (dedupedTypes.length === 1) {
    return (
      <Button
        variant="contained"
        onClick={(e) => {
          e.stopPropagation();
          onSelect(dedupedTypes[0]);
        }}
        sx={buttonStyle}
        startIcon={<AddIcon sx={{ fontSize: BUTTON_SIZES.ICON_FONT_SIZE, mr: 0.25 }} />}
        data-tour-target="create-item-button"
        size="small"
      >
        Add {getDisplayName(dedupedTypes[0])}
      </Button>
    );
  }

  return (
    <>
      <Button
        variant="contained"
        onClick={handleOpen}
        sx={buttonStyle}
        startIcon={<AddIcon sx={{ fontSize: BUTTON_SIZES.ICON_FONT_SIZE, mr: 0.25 }} />}
        endIcon={<KeyboardArrowDownIcon sx={{ fontSize: 13 }} />}
        data-tour-target="create-item-button"
        size="small"
      >
        Add
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        PaperProps={{ sx: menuPaperStyle }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {dedupedTypes.map((type) => (
          <MenuItem key={type} onClick={() => handleSelect(type)} sx={menuItemStyle}>
            <AddIcon sx={{ fontSize: 13, color: 'var(--text-secondary)', flexShrink: 0 }} />
            Add {getDisplayName(type)}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
