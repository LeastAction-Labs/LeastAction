/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import * as React from 'react';

import AccountTreeIcon from '@mui/icons-material/AccountTree';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import LinkIcon from '@mui/icons-material/Link';
import Button from '@mui/material/Button';
import type { MenuProps } from '@mui/material/Menu';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import { alpha, styled } from '@mui/material/styles';

import { BUTTON_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useLinkModalContext } from '@/contexts/LinkModalContext';
import { getSupportedTypes } from '@/services/catalog.service';

import type { CatalogItem, CatalogNode } from '../types';

const StyledMenu = styled((props: MenuProps) => (
  <Menu
    elevation={0}
    anchorOrigin={{
      vertical: 'bottom',
      horizontal: 'right',
    }}
    transformOrigin={{
      vertical: 'top',
      horizontal: 'right',
    }}
    {...props}
  />
))(({ theme }) => ({
  '& .MuiPaper-root': {
    borderRadius: 6,
    marginTop: theme.spacing(0.5),
    minWidth: 'unset',
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.15)',
    '& .MuiMenu-list': {
      padding: '3px 0',
    },
    '& .MuiMenuItem-root': {
      fontSize: '13px',
      minHeight: 'unset',
      lineHeight: '1.4',
      padding: '5px 12px',
      margin: 0,
      borderRadius: 0,
      transition: 'background-color 0.15s ease',
      '& .MuiSvgIcon-root': {
        fontSize: '14px',
        color: 'var(--text-secondary)',
        marginRight: theme.spacing(1),
      },
      '&:hover': {
        backgroundColor: 'var(--bg-tertiary)',
        color: 'var(--text-primary)',
        '& .MuiSvgIcon-root': {
          color: 'var(--text-primary)',
        },
      },
      '&:active': {
        backgroundColor: alpha(theme.palette.primary.main, 0.1),
      },
    },
  },
}));

const StyledButton = styled(Button)(() => ({
  fontSize: BUTTON_SIZES.FONT_SIZE,
  fontWeight: BUTTON_SIZES.FONT_WEIGHT,
  color: 'var(--text-secondary)',
  borderColor: 'var(--border)',
  backgroundColor: 'var(--bg-secondary)',
  padding: BUTTON_SIZES.PADDING,
  height: BUTTON_SIZES.HEIGHT,
  minWidth: '120px',
  textTransform: 'none',
  borderRadius: BUTTON_SIZES.BORDER_RADIUS,
  transition: 'all 0.2s ease',
  '&:hover': {
    borderColor: 'var(--primary-main)',
    color: 'var(--text-primary)',
    backgroundColor: 'var(--bg-tertiary)',
  },
  '& .MuiSvgIcon-root': {
    fontSize: BUTTON_SIZES.ICON_FONT_SIZE,
    transition: 'transform 0.2s ease',
  },
  '&[aria-expanded="true"] .MuiSvgIcon-root': {
    transform: 'rotate(180deg)',
  },
}));

interface OtherActionsDropdownProps {
  item: any;
}

export default function OtherActionsDropdown({ item }: OtherActionsDropdownProps) {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const { catalogType } = useGlobal();
  const { catalogState } = useCatalog();
  const { setLinkModalData } = useLinkModalContext();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleCreateLink = async () => {
    handleClose();
    if (!item) return;
    const { supported_parent_types } = await getSupportedTypes(item.item_type ?? '');
    const isCompatible = (type: string) =>
      supported_parent_types.soft.some((p) => type === p || type.startsWith(p + '.'));
    const availableItems = catalogState.items
      .map((node: CatalogNode) => node.item)
      .filter(
        (item_: CatalogItem) => item_.laui !== item.laui && isCompatible(item_.item_type ?? ''),
      );
    setLinkModalData({
      isOpen: true,
      childItem: item,
      availableItems,
      supportedParentTypes: supported_parent_types.soft,
    });
  };

  const handleAddToWorkflow = () => {
    handleClose();
    setLinkModalData({
      isOpen: true,
      childItem: item,
      itemTypeFilter: 'folder.workflow',
    });
  };

  return (
    <div>
      <StyledButton
        id="other-actions-button"
        aria-controls={open ? 'other-actions-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        variant="outlined"
        disableElevation
        onClick={handleClick}
        endIcon={<KeyboardArrowDownIcon />}
        size="small"
      >
        Actions
      </StyledButton>
      <StyledMenu
        id="other-actions-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'other-actions-button',
        }}
        PaperProps={{
          style: { width: anchorEl?.offsetWidth },
        }}
      >
        {!isMarketplaceCatalog && (
          <MenuItem onClick={() => void handleCreateLink()} disableRipple>
            <LinkIcon />
            Create Link
          </MenuItem>
        )}

        {item?.item_type === 'config' && (
          <MenuItem onClick={handleAddToWorkflow} disableRipple>
            <AccountTreeIcon />
            Add to Workflow
          </MenuItem>
        )}
      </StyledMenu>
    </div>
  );
}
