/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import DarkModeIcon from '@mui/icons-material/DarkMode';
import HomeIcon from '@mui/icons-material/Home';
import LightModeIcon from '@mui/icons-material/LightMode';
import LogoutIcon from '@mui/icons-material/Logout';
import { Box, Chip, IconButton, Tooltip, Typography } from '@mui/material';
import axios from 'axios';

import type { CatalogItem } from '@/components/browse/types';
import { CORE_BACKEND_URL } from '@/config/urls';
import { useTheme } from '@/contexts/ThemeContext';

interface ExplorerHeaderProps {
  folderPath: CatalogItem[];
  onNavigateTo: (item: CatalogItem | null, index: number) => void;
}

interface ExploreViewConfig {
  name: string;
  logo_url: string;
  logo_width: string;
  logo_height: string;
}

const formatName = (name: string) =>
  name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function ExplorerHeader({ folderPath, onNavigateTo }: ExplorerHeaderProps) {
  const { theme, setTheme } = useTheme();
  const [branding, setBranding] = useState<ExploreViewConfig>({
    name: 'Report Explorer',
    logo_url: '',
    logo_width: 'auto',
    logo_height: '24',
  });

  useEffect(() => {
    axios
      .get(`${CORE_BACKEND_URL}/api/v1/system/info`, { withCredentials: true })
      .then((res) => {
        if (res.data?.explore_view) setBranding(res.data.explore_view);
      })
      .catch(() => {});
  }, []);

  const handleLogout = async () => {
    await axios.post(`${CORE_BACKEND_URL}/api/v1/logout`, {}, { withCredentials: true });
    localStorage.removeItem('la_access_token');
    localStorage.removeItem('la_state');
    localStorage.removeItem('auth_request_started');
    window.location.replace('/public/login');
  };

  return (
    <Box
      sx={{
        height: 52,
        display: 'flex',
        alignItems: 'center',
        px: 2.5,
        gap: 2,
        bgcolor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}
    >
      {/* Logo + title */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
        {branding.logo_url ? (
          <img
            src={branding.logo_url}
            alt="logo"
            style={{
              width: branding.logo_width === 'auto' ? 'auto' : `${branding.logo_width}px`,
              height: `${branding.logo_height}px`,
              objectFit: 'contain',
              display: 'block',
            }}
          />
        ) : (
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: '1rem',
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
            }}
          >
            LA
          </Typography>
        )}
        <Typography sx={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          {branding.name}
        </Typography>
        <Chip
          label="Experimental Preview"
          size="small"
          sx={{
            height: 16,
            fontSize: '0.58rem',
            fontWeight: 600,
            bgcolor: 'var(--accent, #7c3aed)',
            color: '#fff',
            letterSpacing: '0.03em',
          }}
        />
      </Box>

      {/* Breadcrumb */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          overflow: 'hidden',
        }}
      >
        <Chip
          icon={<HomeIcon sx={{ fontSize: '14px !important' }} />}
          label="Home"
          size="small"
          onClick={() => onNavigateTo(null, -1)}
          sx={{
            fontSize: '0.7rem',
            height: 22,
            cursor: 'pointer',
            bgcolor: folderPath.length === 0 ? 'var(--text-primary)' : 'var(--bg-primary)',
            color: folderPath.length === 0 ? 'var(--bg-secondary)' : 'var(--text-secondary)',
            border: '1px solid var(--border)',
            '&:hover': {
              bgcolor: folderPath.length === 0 ? 'var(--text-primary)' : 'var(--bg-tertiary)',
            },
          }}
        />
        {folderPath.map((folder, i) => (
          <Box key={folder.laui} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Typography sx={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>›</Typography>
            <Chip
              label={formatName(folder.name)}
              size="small"
              onClick={() => onNavigateTo(folder, i)}
              sx={{
                fontSize: '0.7rem',
                height: 22,
                cursor: 'pointer',
                bgcolor: i === folderPath.length - 1 ? 'var(--text-primary)' : 'var(--bg-primary)',
                color:
                  i === folderPath.length - 1 ? 'var(--bg-secondary)' : 'var(--text-secondary)',
                border: '1px solid var(--border)',
                '&:hover': {
                  bgcolor:
                    i === folderPath.length - 1 ? 'var(--text-primary)' : 'var(--bg-tertiary)',
                },
              }}
            />
          </Box>
        ))}
      </Box>

      {/* Actions */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
        <Tooltip title={theme === 'black' ? 'Switch to light theme' : 'Switch to dark theme'}>
          <IconButton
            size="small"
            onClick={() => setTheme(theme === 'black' ? 'white' : 'black')}
            sx={{
              color: 'var(--text-secondary)',
              p: 0.75,
              '&:hover': { color: 'var(--text-primary)' },
            }}
          >
            {theme === 'black' ? (
              <LightModeIcon sx={{ fontSize: 18 }} />
            ) : (
              <DarkModeIcon sx={{ fontSize: 18 }} />
            )}
          </IconButton>
        </Tooltip>
        {/* <Tooltip title="SQL Query Editor (Experimental Preview)">
          <IconButton
            size="small"
            onClick={() => navigate({ to: '/query' })}
            sx={{ color: 'var(--text-secondary)', p: 0.75, '&:hover': { color: 'var(--text-primary)' } }}
          >
            <TerminalIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip> */}
        {/* <Button
          size="small"
          startIcon={<CodeIcon sx={{ fontSize: 14 }} />}
          onClick={handleSwitchToDeveloper}
          sx={{
            textTransform: 'none',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            borderColor: 'var(--border)',
            '&:hover': { color: 'var(--text-primary)' },
          }}
          variant="outlined"
        >
          Developer View
        </Button> */}
        <Tooltip title="Logout">
          <IconButton
            size="small"
            onClick={() => void handleLogout()}
            sx={{ color: 'var(--text-secondary)', p: 0.75 }}
          >
            <LogoutIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
}
