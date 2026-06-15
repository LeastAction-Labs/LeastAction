/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { AccessTime, HelpOutline, Logout, Settings, Terminal } from '@mui/icons-material';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  Menu,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';

import { CORE_FRONTEND_URL, MARKETPLACE_URL } from '@/config/urls';
import { FONT_SIZES, FONT_WEIGHTS, TRANSITIONS } from '@/constants';
import { useAuth } from '@/contexts/AuthContext';
//import { useMarketplace } from '@/contexts/MarketplaceContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { useTour } from '@/contexts/TourContext';
//import { marketplaceLogout } from '@/services/marketplace.service';
import PhysicsAvatarIcon from '@/utils/physicsIcons';
import { getTimeZoneLabel } from '@/utils/timeFormat';

import { QuickSearch } from '../ui';

type Theme = 'black' | 'white';

const themes: { value: Theme; label: string }[] = [
  { value: 'black', label: 'Black' },
  { value: 'white', label: 'White' },
];

// Component-specific styles
const styles = {
  header: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    py: 0.5,
    px: 1.5,
    gap: 4,
    bgcolor: 'var(--bg-primary)',
    borderBottom: '1px solid var(--border)',
  },
  title: {
    fontWeight: FONT_WEIGHTS.BOLD,
    color: 'var(--text-primary)',
  },
  settingsButton: {
    color: 'var(--text-secondary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
    },
  },
  physicsButton: {
    color: 'var(--text-primary)',
    bgcolor: 'var(--bg-secondary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&:hover': {
      bgcolor: 'var(--bg-tertiary)',
    },
  },
  themeMenu: {
    '& .MuiPaper-root': {
      bgcolor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      border: 1,
      borderColor: 'var(--border)',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    },
  },
  menuHeader: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  menuItem: {
    color: 'var(--text-primary)',
    transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
    '&.Mui-selected': {
      bgcolor: 'var(--bg-selected)',
      color: 'var(--text-primary)',
      fontWeight: FONT_WEIGHTS.WEIGHT_500,
      '&:hover': {
        bgcolor: 'var(--bg-selected)',
      },
    },
    '&:hover': {
      bgcolor: 'var(--bg-tertiary)',
    },
  },
  windowControl: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    bgcolor: 'white',
  },
  windowControlBorder: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    border: 2,
    borderColor: 'white',
  },
  dialogField: {
    '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
    '& .MuiInputLabel-root.Mui-focused': { color: 'var(--text-primary)' },
    '& .MuiOutlinedInput-root': {
      color: 'var(--text-primary)',
      '& fieldset': { borderColor: 'var(--border)' },
      '&:hover fieldset': { borderColor: 'var(--text-secondary)' },
      '&.Mui-focused fieldset': { borderColor: 'var(--text-primary)' },
    },
    '& .MuiSelect-icon': { color: 'var(--text-secondary)' },
  },
};

export default function TopHeader() {
  const { theme, setTheme } = useTheme();
  const { logout } = useAuth();
  const { timeZone, toggleTimeZone } = useTimeFormat();
  const { openLanding } = useTour();
  /*
  const {
    userAuthenticated: userLoggedInToMarketplace,
    triggerReload: triggerMarketplaceContextReload,
  } = useMarketplace();
  */

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [themeAnchorEl, setThemeAnchorEl] = useState<null | HTMLElement>(null);
  const [helpAnchorEl, setHelpAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const themeOpen = Boolean(themeAnchorEl);

  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [fbName, setFbName] = useState('');
  const [fbEmail, setFbEmail] = useState('');
  const [fbCompany, setFbCompany] = useState('');
  const [fbTeamSize, setFbTeamSize] = useState('');
  const [fbMessage, setFbMessage] = useState('');
  const [fbStatus, setFbStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [fbError, setFbError] = useState('');

  /*
  const handleMarketplace = async () => {
    if (userLoggedInToMarketplace) {
      await marketplaceLogout();
      window.location.reload();
    } else {
      const state =
        Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
      const x = JSON.parse(localStorage.getItem('marketplace_auth_state') || '[]');
      x.push(state);
      localStorage.setItem('marketplace_auth_state', JSON.stringify(x));
      localStorage.setItem('marketplace_auth_started', 'true');
      const clientId = 'core-client';
      const redirectUri = encodeURIComponent(`${CORE_FRONTEND_URL}/public/marketplace-callback`);
      const marketplaceAuthUrl = `${MARKETPLACE_URL}/api/v1/marketplace/auth/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&state=${state}`;
      window.open(marketplaceAuthUrl, '_blank');
      while (localStorage.getItem('marketplace_auth_started')) {
        console.log('checking if marketplace auth completed');
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      triggerMarketplaceContextReload();
    }
  };
  */
  const handleSettingsClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleThemeMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setThemeAnchorEl(event.currentTarget);
  };

  const handleThemeMenuClose = () => {
    setThemeAnchorEl(null);
  };

  const handleThemeSelect = (selectedTheme: Theme) => {
    setTheme(selectedTheme);
    handleThemeMenuClose();
    handleClose();
  };
  const handleLogout = async () => {
    await logout();
    handleClose();
    window.location.replace(`${CORE_FRONTEND_URL}/public/login`);
  };

  const handleHelpOpen = (event: React.MouseEvent<HTMLElement>) => {
    setHelpAnchorEl(event.currentTarget);
  };

  const handleHelpClose = () => {
    setHelpAnchorEl(null);
  };

  const handleFeedbackOpen = () => {
    handleHelpClose();
    setFeedbackOpen(true);
  };

  const handleFeedbackClose = () => {
    setFeedbackOpen(false);
    setTimeout(() => {
      setFbName('');
      setFbEmail('');
      setFbCompany('');
      setFbTeamSize('');
      setFbMessage('');
      setFbStatus('idle');
      setFbError('');
    }, 200);
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFbStatus('loading');
    setFbError('');
    try {
      const res = await fetch(`${MARKETPLACE_URL}/api/v1/marketplace/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: fbName,
          email: fbEmail,
          company: fbCompany,
          team_size: fbTeamSize,
          message: fbMessage,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as { detail?: string })?.detail || 'Failed to send feedback');
      }
      setFbStatus('success');
    } catch (err: unknown) {
      setFbError(err instanceof Error ? err.message : 'Failed to send feedback');
      setFbStatus('error');
    }
  };

  return (
    <Box sx={styles.header}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
          component="img"
          src="/Logo_square.svg"
          alt="LeastAction"
          sx={{
            height: 28,
            width: 28,
            display: 'block',
            filter: theme === 'black' ? 'invert(1)' : 'none',
          }}
        />
        <Typography variant="h6" sx={styles.title}>
          LeastAction
          <span
            style={{
              marginLeft: '4px',
              fontSize: '0.7em',
              verticalAlign: 'super',
              color: '#5B9BD5', // Workflow blue
              fontWeight: 'bold',
            }}
          >
            W
          </span>
        </Typography>
      </Box>

      <Box sx={{ ml: 'auto', display: 'flex', width: 600, alignItems: 'center', gap: 2 }}>
        <QuickSearch
          label="Global search"
          returnUrl={true}
          ignoreProjectScope={true}
          onSelect={(url) => (window.location.href = url as string)}
          inputSx={{
            '& .MuiOutlinedInput-root': {
              backgroundColor: 'var(--bg-secondary)',
              '& fieldset': { borderColor: 'rgba(255,255,255,0.12)' },
              '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.24)' },
            },
          }}
        />
      </Box>

      <Box sx={{ ml: 'auto', display: 'flex', alignItems: 'center', gap: 0.1 }}>
        {/*
          <Button onClick={() => void handleMarketplace()}>
              userLoggedInToMarketplace ? 'Logout from marketplace' : 'Login to marketplace'}
          </Button>
          */}
        <Button
          onClick={toggleTimeZone}
          size="small"
          startIcon={<AccessTime sx={{ fontSize: 16 }} />}
          sx={{
            color: 'var(--text-secondary)',
            textTransform: 'none',
            fontSize: FONT_SIZES.XS,
            fontWeight: FONT_WEIGHTS.WEIGHT_500,
            minWidth: 'auto',
            px: 1,
            borderRadius: 1,
            border: '1px solid var(--border)',
            transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
            '&:hover': {
              bgcolor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              borderColor: 'var(--text-secondary)',
            },
          }}
          title={`Currently showing ${timeZone === 'utc' ? 'UTC' : 'local'} time. Click to switch to ${timeZone === 'utc' ? 'local' : 'UTC'}.`}
        >
          {timeZone === 'utc' ? 'UTC' : getTimeZoneLabel()}
        </Button>
        <IconButton onClick={handleHelpOpen} sx={styles.settingsButton} title="Help">
          <HelpOutline />
        </IconButton>
        <Menu
          anchorEl={helpAnchorEl}
          open={Boolean(helpAnchorEl)}
          onClose={handleHelpClose}
          sx={styles.themeMenu}
        >
          <MenuItem
            onClick={() => {
              handleHelpClose();
              openLanding();
            }}
            sx={styles.menuItem}
          >
            Getting Started Tour
          </MenuItem>
          <MenuItem onClick={handleFeedbackOpen} sx={styles.menuItem}>
            Feedback
          </MenuItem>
        </Menu>
        <IconButton
          onClick={handleSettingsClick}
          sx={styles.settingsButton}
          aria-controls={open ? 'settings-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
        >
          <Settings />
        </IconButton>
        <IconButton sx={styles.physicsButton}>
          <PhysicsAvatarIcon size={30} />
        </IconButton>
        <Menu
          id="settings-menu"
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          sx={styles.themeMenu}
        >
          <MenuItem
            onClick={() => {
              handleClose();
              window.open('/mcp-token', '_blank');
            }}
            sx={styles.menuItem}
          >
            <Terminal sx={{ mr: 1, fontSize: 20, verticalAlign: 'middle' }} />
            Claude Code + MCP
          </MenuItem>
          <MenuItem onClick={handleThemeMenuOpen} sx={styles.menuItem}>
            Theme
          </MenuItem>
          <MenuItem onClick={() => void handleLogout()} sx={styles.menuItem}>
            <Logout sx={{ mr: 1, fontSize: 20, verticalAlign: 'middle' }} />
            Logout
          </MenuItem>
        </Menu>
        <Menu
          id="theme-submenu"
          anchorEl={themeAnchorEl}
          open={themeOpen}
          onClose={handleThemeMenuClose}
          anchorOrigin={{
            vertical: 'top',
            horizontal: 'left',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
          sx={styles.themeMenu}
        >
          <MenuItem disabled sx={styles.menuHeader}>
            Select Theme
          </MenuItem>
          {themes.map((themeOption) => (
            <MenuItem
              key={themeOption.value}
              onClick={() => handleThemeSelect(themeOption.value)}
              selected={theme === themeOption.value}
              sx={styles.menuItem}
            >
              {themeOption.label}
            </MenuItem>
          ))}
        </Menu>
      </Box>

      <Dialog
        open={feedbackOpen}
        onClose={handleFeedbackClose}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
          },
        }}
      >
        <DialogTitle sx={{ color: 'var(--text-primary)' }}>Send Feedback</DialogTitle>
        {fbStatus === 'success' ? (
          <DialogContent>
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <Typography sx={{ fontWeight: FONT_WEIGHTS.BOLD, color: 'var(--text-primary)' }}>
                Feedback sent!
              </Typography>
              <Typography
                sx={{
                  color: 'var(--text-secondary)',
                  fontSize: FONT_SIZES.SM,
                  mt: 1,
                }}
              >
                We'll get back to you within 1 business day.
              </Typography>
              <Button onClick={handleFeedbackClose} sx={{ mt: 2, color: 'var(--text-primary)' }}>
                Close
              </Button>
            </Box>
          </DialogContent>
        ) : (
          <form onSubmit={(e) => void handleFeedbackSubmit(e)}>
            <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
              {fbError && (
                <Typography sx={{ color: 'error.main', fontSize: FONT_SIZES.SM }}>
                  {fbError}
                </Typography>
              )}
              <TextField
                label="Name"
                required
                size="small"
                value={fbName}
                onChange={(e) => setFbName(e.target.value)}
                sx={styles.dialogField}
              />
              <TextField
                label="Work email"
                type="email"
                required
                size="small"
                value={fbEmail}
                onChange={(e) => setFbEmail(e.target.value)}
                sx={styles.dialogField}
              />
              <TextField
                label="Company"
                required
                size="small"
                value={fbCompany}
                onChange={(e) => setFbCompany(e.target.value)}
                sx={styles.dialogField}
              />
              <FormControl size="small" required sx={styles.dialogField}>
                <InputLabel>Team size</InputLabel>
                <Select
                  value={fbTeamSize}
                  label="Team size"
                  onChange={(e) => setFbTeamSize(e.target.value)}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        bgcolor: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                      },
                    },
                  }}
                >
                  <MenuItem value="individual">Individual</MenuItem>
                  <MenuItem value="upto25">Up to 25</MenuItem>
                  <MenuItem value="25plus">25+</MenuItem>
                </Select>
              </FormControl>
              <TextField
                label="Message"
                required
                multiline
                rows={3}
                value={fbMessage}
                onChange={(e) => setFbMessage(e.target.value)}
                sx={styles.dialogField}
              />
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={handleFeedbackClose} sx={{ color: 'var(--text-secondary)' }}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={fbStatus === 'loading'}
                startIcon={
                  fbStatus === 'loading' ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : undefined
                }
              >
                Send
              </Button>
            </DialogActions>
          </form>
        )}
      </Dialog>
    </Box>
  );
}
