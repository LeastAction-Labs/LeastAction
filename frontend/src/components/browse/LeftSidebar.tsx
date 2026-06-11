/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { useNavigate, useRouterState } from '@tanstack/react-router';

import {
  // Search as SearchIcon,
  AutoAwesome as AIAssistantIcon,
  AdminPanelSettings as AdminPanelSettingsIcon,
  BugReport as BugReportIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Close as CloseIcon,
  Explore as ExploreIcon,
  Folder as FolderIcon,
  HourglassEmpty as PendingPubIcon,
  Speed as PerformanceIcon,
  CheckCircle as PublisherIcon,
  Terminal as QueryEditorIcon,
  PersonAdd as RequestPubIcon,
} from '@mui/icons-material';
import { Box, Dialog, DialogContent, DialogTitle, IconButton, Tooltip } from '@mui/material';

// @ts-expect-error - no type declarations
import PerformanceDashboard from '@/components/logs/PerformanceDashboard';
import { useAuth } from '@/contexts/AuthContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { requestPublish } from '@/services/marketplace.service';

import { FONT_SIZES, TRANSITIONS } from '../../constants';

type LeftSidebarIcon =
  | 'document'
  | 'search'
  | 'ai-assistant'
  | 'performance'
  | 'marketplace'
  | 'admin'
  | 'query'
  | 'debug';

const styles = {
  container: {
    width: 48,
    borderRight: 1,
    borderTop: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-primary)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    pt: 0,
    pb: 2,
    gap: 1,
    flexShrink: 0,
  },
  iconButton: (isSelected: boolean) => ({
    position: 'relative',
    color: isSelected ? 'var(--accent)' : 'var(--text-secondary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
    },
    '&::before': isSelected
      ? {
          content: '""',
          position: 'absolute',
          left: -8,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 3,
          height: '60%',
          bgcolor: 'var(--accent)',
          borderRadius: '0 2px 2px 0',
        }
      : {},
  }),
};

export default function LeftSidebar() {
  const navigate = useNavigate();
  const { setCatalogType, folderSidebarState, setFolderSidebarState } = useGlobal();
  const { authState } = useAuth();
  const {
    user: marketplaceUser,
    publishAccess,
    userAuthenticated: userAuthenticatedToMarketplace,
    triggerReload,
  } = useMarketplace();

  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const routeIcon: LeftSidebarIcon = pathname.startsWith('/marketplace')
    ? 'marketplace'
    : pathname.startsWith('/ai')
      ? 'ai-assistant'
      : pathname.startsWith('/query')
        ? 'query'
        : pathname.startsWith('/debug')
          ? 'debug'
          : 'document';

  const [selectedIcon, setSelectedIcon] = useState<LeftSidebarIcon>(routeIcon);
  const [perfOpen, setPerfOpen] = useState(false);

  const activeIcon = perfOpen ? 'performance' : routeIcon !== 'document' ? routeIcon : selectedIcon;

  const handleRequestPublish = async () => {
    try {
      await requestPublish();
      triggerReload();
    } catch (e: any) {
      console.log(`error when requesting for publish: ${e.message}`);
    }
  };
  const handleIconClick = (icon: LeftSidebarIcon) => {
    setSelectedIcon(icon);
    switch (icon) {
      case 'document':
        setCatalogType(CatalogType.BROWSE);
        void navigate({ to: '/path', search: {} });
        break;
      case 'search':
        break;
      case 'ai-assistant':
        void navigate({ to: '/ai/create', search: { sessionId: undefined } });
        break;
      case 'performance':
        setPerfOpen(true);
        break;
      case 'marketplace':
        setCatalogType(CatalogType.MARKETPLACE);
        void navigate({ to: '/marketplace' });
        break;
      case 'admin':
        void navigate({ to: '/admin' });
        break;
      case 'query':
        void navigate({ to: '/query' });
        break;
      case 'debug':
        void navigate({ to: '/debug', search: { session_id: '' } });
        break;
    }
  };

  return (
    <>
      <Box sx={styles.container}>
        {/* Toggle folder sidebar button */}
        <IconButton
          onClick={(e) => {
            e.stopPropagation();
            setFolderSidebarState({
              ...folderSidebarState,
              isCollapsed: !folderSidebarState.isCollapsed,
            });
          }}
          sx={{
            color: 'var(--text-secondary)',
            transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
            '&:hover': {
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
            },
            pointerEvents: 'auto',
            cursor: 'pointer',
          }}
          aria-label={folderSidebarState.isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {folderSidebarState.isCollapsed ? (
            <ChevronRightIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
          ) : (
            <ChevronLeftIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
          )}
        </IconButton>
        <IconButton
          onClick={() => handleIconClick('document')}
          sx={styles.iconButton(activeIcon === 'document')}
        >
          <FolderIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
        </IconButton>
        {/* <IconButton
          onClick={() => handleIconClick("search")}
          sx={styles.iconButton(activeIcon === "search")}
        >
          <SearchIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
        </IconButton> */}
        <IconButton
          onClick={() => handleIconClick('ai-assistant')}
          sx={styles.iconButton(activeIcon === 'ai-assistant')}
        >
          <AIAssistantIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
        </IconButton>
        <Tooltip title="SQL Query Editor (Experimental Preview)" placement="right">
          <IconButton
            onClick={() => handleIconClick('query')}
            sx={styles.iconButton(activeIcon === 'query')}
            aria-label="SQL Query Editor (Experimental Preview)"
          >
            <QueryEditorIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
          </IconButton>
        </Tooltip>
        {import.meta.env.DEV && (
          <IconButton
            onClick={() => handleIconClick('performance')}
            sx={styles.iconButton(activeIcon === 'performance')}
            aria-label="Performance Dashboard"
          >
            <PerformanceIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
          </IconButton>
        )}
        <IconButton
          onClick={() => handleIconClick('debug')}
          sx={styles.iconButton(activeIcon === 'debug')}
          aria-label="Debug"
        >
          <BugReportIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
        </IconButton>
        <IconButton
          onClick={() => handleIconClick('marketplace')}
          sx={styles.iconButton(activeIcon === 'marketplace')}
          aria-label="Explore Marketplace"
        >
          <ExploreIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
        </IconButton>
        {authState.isAdmin && (
          <IconButton
            onClick={() => handleIconClick('admin')}
            sx={styles.iconButton(selectedIcon === 'admin')}
            aria-label="Admin Panel"
          >
            <AdminPanelSettingsIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
          </IconButton>
        )}
        {userAuthenticatedToMarketplace && publishAccess && (
          <Tooltip title="Publisher" placement="right">
            <IconButton sx={{ color: '#4caf50', '&:hover': { bgcolor: 'var(--bg-tertiary)' } }}>
              <PublisherIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
            </IconButton>
          </Tooltip>
        )}
        {userAuthenticatedToMarketplace && marketplaceUser?.publish_requested && !publishAccess && (
          <Tooltip title="Publisher Request Pending" placement="right">
            <span>
              <IconButton disabled sx={{ color: '#ff9800 !important', opacity: '1 !important' }}>
                <PendingPubIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
              </IconButton>
            </span>
          </Tooltip>
        )}
        {userAuthenticatedToMarketplace &&
          !marketplaceUser?.publish_requested &&
          !publishAccess && (
            <Tooltip title="Become a Publisher" placement="right">
              <IconButton
                onClick={() => void handleRequestPublish()}
                sx={{
                  color: 'var(--text-secondary)',
                  '&:hover': {
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                }}
              >
                <RequestPubIcon sx={{ fontSize: FONT_SIZES.ICON_XL }} />
              </IconButton>
            </Tooltip>
          )}
      </Box>

      {/* Performance Dashboard Dialog */}
      <Dialog
        open={perfOpen}
        onClose={() => {
          setPerfOpen(false);
          setSelectedIcon('document');
        }}
        maxWidth="xl"
        fullWidth
        PaperProps={{ sx: { height: '90vh', borderRadius: 2 } }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border)',
          }}
        >
          Performance Dashboard
          <IconButton
            onClick={() => {
              setPerfOpen(false);
              setSelectedIcon('document');
            }}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <PerformanceDashboard />
        </DialogContent>
      </Dialog>
    </>
  );
}
