/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import CloseIcon from '@mui/icons-material/Close';
import CloseFullscreenIcon from '@mui/icons-material/CloseFullscreen';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import MenuIcon from '@mui/icons-material/Menu';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import PictureInPictureAltIcon from '@mui/icons-material/PictureInPictureAlt';
import PushPinIcon from '@mui/icons-material/PushPin';
import PushPinOutlinedIcon from '@mui/icons-material/PushPinOutlined';
import RemoveIcon from '@mui/icons-material/Remove';
import ViewSidebarOutlinedIcon from '@mui/icons-material/ViewSidebarOutlined';
import { Box, Fab, IconButton, Paper, Tooltip, Typography } from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { useChatDock } from '@/contexts/ChatDockContext';
import { useTour } from '@/contexts/TourContext';
import { getMyBusinessChatConfig } from '@/services/admin.service';
import { physicsIcons } from '@/utils/physicsIcons';

import ChatMenu from './ChatMenu';
import ChatPanel from './ChatPanel';
import ProviderList, { type ProviderConfig } from './ProviderList';

function PhysicsIcon({ size }: { size: number }) {
  const stored = localStorage.getItem('selected-physics-icon');
  const icon =
    (stored ? physicsIcons.find((i) => i.id === Number(stored)) : null) ?? physicsIcons[1];
  return (
    <Box sx={{ width: size, height: size, color: 'inherit', display: 'flex' }}>{icon.svg}</Box>
  );
}

function getSelectedIconName(): string {
  const stored = localStorage.getItem('selected-physics-icon');
  const icon =
    (stored ? physicsIcons.find((i) => i.id === Number(stored)) : null) ?? physicsIcons[1];
  return icon.name.toLowerCase();
}

function getIdleAnimation(iconName: string): { anim: string; duration: string; easing: string } {
  if (['pendulum', 'harmonic', 'oscillation'].includes(iconName))
    return { anim: 'laPhysicsSwing', duration: '2.5s', easing: 'ease-in-out' };
  if (['orbit', 'atom', 'vortex', 'centripetal', 'torque', 'spin'].includes(iconName))
    return { anim: 'laPhysicsRotate', duration: '3s', easing: 'linear' };
  if (
    ['wave', 'doppler', 'frequency', 'resonance', 'interference', 'diffraction'].includes(iconName)
  )
    return { anim: 'laPhysicsBob', duration: '1.8s', easing: 'ease-in-out' };
  if (['quantum', 'superposition', 'uncertainty', 'entanglement'].includes(iconName))
    return { anim: 'laPhysicsJitter', duration: '0.35s', easing: 'linear' };
  return { anim: 'laPhysicsBreathe', duration: '2s', easing: 'ease-in-out' };
}

const BASE_WIDTH = 380;
const BASE_HEIGHT = 520;

const DOCK_PREF_KEY = 'la_chat_dock_pref';
const DOCK_WIDTH_KEY = 'la_chat_dock_width';
const DOCK_MIN_WIDTH = 320;
const DOCK_MAX_WIDTH = 720;
const DOCK_DEFAULT_WIDTH = 420;

type ChatMode = 'popup' | 'docked';

function readDockPref(): ChatMode | null {
  const v = localStorage.getItem(DOCK_PREF_KEY);
  return v === 'docked' || v === 'popup' ? v : null;
}

function readDockWidth(): number {
  const v = Number(localStorage.getItem(DOCK_WIDTH_KEY));
  if (!v || Number.isNaN(v)) return DOCK_DEFAULT_WIDTH;
  return Math.max(DOCK_MIN_WIDTH, Math.min(DOCK_MAX_WIDTH, v));
}

export default function ChatbotWidget() {
  const { setReservedRight } = useChatDock();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [expanded, setExpanded] = useState(false);
  // Dock state — popup is the first-time default; a stored preference can make
  // the docked layout open automatically on subsequent visits.
  const [mode, setMode] = useState<ChatMode>('popup');
  const [dockHidden, setDockHidden] = useState(false);
  const [dockDefault, setDockDefault] = useState<ChatMode | null>(() => readDockPref());
  const [dockWidth, setDockWidth] = useState<number>(() => readDockWidth());
  const dockResizing = useRef(false);
  const [view, setView] = useState<'select' | 'agent'>('select');
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const [chatKey, setChatKey] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isBusinessPreconfig, setIsBusinessPreconfig] = useState(false);
  const defaultProviderConfigRef = useRef<ProviderConfig | null>(null);
  const [isIdle, setIsIdle] = useState(false);
  const [piPulse, setPiPulse] = useState(false);
  const piPulseFiredRef = useRef(false);
  const { activeTour, currentStepIndex } = useTour();

  const [fabPos, setFabPos] = useState<{ bottom: number; right: number }>({
    bottom: 24,
    right: 24,
  });
  const dragging = useRef(false);
  const dragOffset = useRef({ x: 0, y: 0 });

  const onFabMouseDown = useCallback(
    (e: React.MouseEvent) => {
      // Only start drag on direct FAB click, not child clicks that trigger open
      dragging.current = true;
      dragOffset.current = {
        x: e.clientX - (window.innerWidth - fabPos.right - 56),
        y: e.clientY - (window.innerHeight - fabPos.bottom - 56),
      };
      e.preventDefault();
    },
    [fabPos],
  );

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const newRight = window.innerWidth - e.clientX + dragOffset.current.x - 56;
      const newBottom = window.innerHeight - e.clientY + dragOffset.current.y - 56;
      setFabPos({
        right: Math.max(8, Math.min(newRight, window.innerWidth - 64)),
        bottom: Math.max(8, Math.min(newBottom, window.innerHeight - 64)),
      });
    };
    const onMouseUp = () => {
      dragging.current = false;
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);
  const tourPrefill = activeTour?.steps[currentStepIndex]?.chatbotPrefill ?? null;


  const showDockPanel = open && mode === 'docked' && !dockHidden;
  const showPopupPanel = open && mode === 'popup';
   const showFab = mode === 'popup' || (mode === 'docked' && (!open || dockHidden));
  useEffect(() => {
    if (readDockPref() === 'docked') {
      setMode('docked');
      setOpen(true);
      setMinimized(false);
    }
  }, []);

  useEffect(() => {
    setReservedRight(showDockPanel ? dockWidth : 0);
    return () => setReservedRight(0);
  }, [showDockPanel, dockWidth, setReservedRight]);


  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dockResizing.current) return;
      const next = Math.max(
        DOCK_MIN_WIDTH,
        Math.min(DOCK_MAX_WIDTH, window.innerWidth - e.clientX),
      );
      setDockWidth(next);
    };
    const onUp = () => {
      if (!dockResizing.current) return;
      dockResizing.current = false;
      document.body.style.userSelect = '';
      localStorage.setItem(DOCK_WIDTH_KEY, String(dockWidth));
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dockWidth]);

  const startDockResize = (e: React.MouseEvent) => {
    e.preventDefault();
    dockResizing.current = true;
    document.body.style.userSelect = 'none';
  };


  const handleDock = () => {
    setMode('docked');
    setDockHidden(false);
    setExpanded(false);
    setMinimized(false);
    setOpen(true);
    setMenuOpen(false);
  };

  const handleUndock = () => {
    setMode('popup');
    setDockHidden(false);
    setOpen(true);
  };

  const handleHideDock = () => {
    setDockHidden(true);
    setMenuOpen(false);
  };

  const handleRevealDock = () => {
    setMode('docked');
    setDockHidden(false);
    setOpen(true);
  };
  const handleToggleDockDefault = () => {
    if (dockDefault === 'docked') {
      localStorage.removeItem(DOCK_PREF_KEY);
      setDockDefault(null);
    } else {
      localStorage.setItem(DOCK_PREF_KEY, 'docked');
      setDockDefault('docked');
    }
  };

  useEffect(() => {
    let idleTimer: ReturnType<typeof setTimeout>;
    const IDLE_MS = 5 * 60 * 1000;
    const resetIdle = () => {
      setIsIdle(false);
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => setIsIdle(true), IDLE_MS);
    };
    window.addEventListener('mousemove', resetIdle);
    window.addEventListener('keydown', resetIdle);
    window.addEventListener('click', resetIdle);
    resetIdle();
    return () => {
      clearTimeout(idleTimer);
      window.removeEventListener('mousemove', resetIdle);
      window.removeEventListener('keydown', resetIdle);
      window.removeEventListener('click', resetIdle);
    };
  }, []);

  useEffect(() => {
    const checkPiTime = () => {
      const now = new Date();
      const h = now.getHours();
      const m = now.getMinutes();
      if ((h === 3 || h === 15) && m === 14 && !piPulseFiredRef.current) {
        piPulseFiredRef.current = true;
        setPiPulse(true);
        setTimeout(() => {
          setPiPulse(false);
          piPulseFiredRef.current = false;
        }, 10000);
      }
    };
    checkPiTime();
    const interval = setInterval(checkPiTime, 30000);
    return () => clearInterval(interval);
  }, []);

  // Load the per-user default chat config (set from the admin dashboard MCP
  // Access tab). When present, the widget opens straight onto that agent and
  // keeps it as the persistent default — independent of the view mode.
  useEffect(() => {
    void getMyBusinessChatConfig().then((config) => {
      if (config?.chat_agent_laui && config?.chat_connection_laui) {
        const defaultConfig: ProviderConfig = {
          aiChatLaui: config.chat_agent_laui,
          aiChatName: config.chat_agent_name ?? 'AI Agent',
          aiProvider: config.chat_agent_provider ?? 'anthropic',
          connectionLaui: config.chat_connection_laui,
        };
        defaultProviderConfigRef.current = defaultConfig;
        setProviderConfig(defaultConfig);
        setView('agent');
        setIsBusinessPreconfig(true);
      }
    });
  }, []);

  const handleProviderSelect = (config: ProviderConfig) => {
    setProviderConfig(config);
    setView('agent');
  };

  const handleBack = () => {
    setView('select');
    setProviderConfig(null);
  };

  // X — clears the current conversation. If a business default agent is
  // configured, fall back to it instead of the provider-selection dropdown so
  // the default stays persistent across open/close (not just on refresh).
  const handleClose = () => {
    setOpen(false);
    setExpanded(false);
    setMenuOpen(false);
    if (defaultProviderConfigRef.current) {
      setProviderConfig(defaultProviderConfigRef.current);
      setView('agent');
    } else {
      setView('select');
      setProviderConfig(null);
    }
    setChatKey((k) => k + 1);
  };

  // Minimize — shrinks to header bar only, keeps all state intact
  const handleMinimize = () => {
    setMinimized((m) => !m);
  };

  // New session — fresh chat on the default agent when configured, otherwise
  // back to the provider-selection view.
  const handleNewSession = () => {
    if (defaultProviderConfigRef.current) {
      setProviderConfig(defaultProviderConfigRef.current);
      setView('agent');
    } else {
      setView('select');
      setProviderConfig(null);
    }
    setChatKey((k) => k + 1);
  };

  // Load a specific config (a resumed session from Recents, or an agent +
  // connection picked in the menu) into a fresh ChatPanel.
  const handleSelectConfig = (config: ProviderConfig) => {
    setProviderConfig(config);
    setView('agent');
    setChatKey((k) => k + 1);
  };

  const fabDraggedRef = useRef(false);
  const fabMouseDownPos = useRef({ x: 0, y: 0 });

  const handleFabMouseDown = useCallback(
    (e: React.MouseEvent) => {
      fabMouseDownPos.current = { x: e.clientX, y: e.clientY };
      fabDraggedRef.current = false;
      onFabMouseDown(e);
    },
    [onFabMouseDown],
  );

  // FAB — toggles open, restores from minimized if needed
  const handleFabClick = (e: React.MouseEvent) => {
    const dx = Math.abs(e.clientX - fabMouseDownPos.current.x);
    const dy = Math.abs(e.clientY - fabMouseDownPos.current.y);
    if (dx > 4 || dy > 4) return; // was a drag, not a click
    if (mode === 'docked') {
      handleRevealDock();
      return;
    }
    if (open && !minimized) {
      setMinimized(true);
    } else {
      setOpen(true);
      setMinimized(false);
    }
  };

  const width = minimized ? 400 : expanded ? BASE_WIDTH * 2 : BASE_WIDTH;
  const height = minimized ? 'auto' : expanded ? Math.round(BASE_HEIGHT * 1.6) : BASE_HEIGHT;

  const iconBtnSx = { color: 'var(--text-secondary)', p: 0.5 } as const;

  const renderHeader = (isDocked: boolean) => (
    <Box
      sx={{
        px: 2,
        py: 1.5,
        bgcolor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 0.5,
      }}
    >
      {(isDocked || !minimized) && (
        <IconButton size="small" onClick={() => setMenuOpen((m) => !m)} sx={iconBtnSx} title="Menu">
          <MenuIcon sx={{ fontSize: 20 }} />
        </IconButton>
      )}
      {view === 'agent' && !isBusinessPreconfig && (
        <IconButton size="small" onClick={handleBack} sx={iconBtnSx} title="Back">
          <ArrowBackIcon sx={{ fontSize: 18 }} />
        </IconButton>
      )}
      <PhysicsIcon size={20} />
      <Typography
        sx={{
          flex: 1,
          ml: 0.5,
          fontSize: FONT_SIZES.SM,
          fontWeight: FONT_WEIGHTS.WEIGHT_500,
          color: 'var(--text-primary)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {view === 'select' ? 'Choose AI Agent' : providerConfig?.aiChatName}
      </Typography>
      <Tooltip title="AI Tech Intro">
        <IconButton
          size="small"
          onClick={() =>
            (window.location.href =
              '/path?itemtype=doc.file&itemname=AI%20Tech%20Intro&laui=getting-started-AI_tech_intro')
          }
          sx={iconBtnSx}
        >
          <HelpOutlineIcon sx={{ fontSize: 16 }} />
        </IconButton>
      </Tooltip>
      {isDocked ? (
        <>
          <Tooltip
            title={dockDefault === 'docked' ? 'Remove docked default' : 'Open docked by default'}
          >
            <IconButton
              size="small"
              onClick={handleToggleDockDefault}
              sx={{
                ...iconBtnSx,
                color: dockDefault === 'docked' ? 'var(--accent)' : 'var(--text-secondary)',
              }}
            >
              {dockDefault === 'docked' ? (
                <PushPinIcon sx={{ fontSize: 16 }} />
              ) : (
                <PushPinOutlinedIcon sx={{ fontSize: 16 }} />
              )}
            </IconButton>
          </Tooltip>
          <Tooltip title="Undock to popup">
            <IconButton size="small" onClick={handleUndock} sx={iconBtnSx}>
              <PictureInPictureAltIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Hide dock">
            <IconButton size="small" onClick={handleHideDock} sx={iconBtnSx}>
              <ChevronRightIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </>
      ) : (
        <>
          <Tooltip title="Dock to right">
            <IconButton size="small" onClick={handleDock} sx={iconBtnSx}>
              <ViewSidebarOutlinedIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
          <IconButton
            size="small"
            onClick={() => setExpanded((e) => !e)}
            sx={iconBtnSx}
            title={expanded ? 'Shrink' : 'Expand'}
          >
            {expanded ? (
              <CloseFullscreenIcon sx={{ fontSize: 16 }} />
            ) : (
              <OpenInFullIcon sx={{ fontSize: 16 }} />
            )}
          </IconButton>
          <IconButton
            size="small"
            onClick={handleMinimize}
            sx={iconBtnSx}
            title={minimized ? 'Restore' : 'Minimize'}
          >
            <RemoveIcon sx={{ fontSize: 18 }} />
          </IconButton>
        </>
      )}
      <IconButton size="small" onClick={handleClose} sx={iconBtnSx} title="Close">
        <CloseIcon sx={{ fontSize: 18 }} />
      </IconButton>
    </Box>
  );

  const renderBody = (isDocked: boolean) => (
    <Box
      sx={{
        // display:none (popup minimized) keeps components mounted with state intact
        display: !isDocked && minimized ? 'none' : 'flex',
        flex: 1,
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {view === 'select' ? (
        <ProviderList onSelect={handleProviderSelect} prefill={tourPrefill} />
      ) : providerConfig ? (
        <ChatPanel key={chatKey} providerConfig={providerConfig} />
      ) : null}

      <ChatMenu
        open={menuOpen}
        showAgentSelector={!isBusinessPreconfig}
        onNewSession={handleNewSession}
        onSelectConfig={handleSelectConfig}
        onClose={() => setMenuOpen(false)}
      />
    </Box>
  );

  return (
    <>
      {/* Popup dialog */}
      {showPopupPanel && (
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            bottom: fabPos.bottom + 64,
            right: fabPos.right,
            width,
            height,
            zIndex: 1300,
            borderRadius: minimized ? BORDER_RADIUS.MD : BORDER_RADIUS.LG,
            border: '1px solid var(--border)',
            bgcolor: 'var(--bg-primary)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            transition: 'width 0.2s ease, height 0.2s ease',
          }}
        >
          {renderHeader(false)}
          {renderBody(false)}
        </Paper>
      )}

      {/* Docked panel — full-height right column; the app shell reserves its width */}
      {showDockPanel && (
        <Paper
          elevation={8}
          sx={{
            position: 'fixed',
            top: 0,
            right: 0,
            bottom: 0,
            width: dockWidth,
            zIndex: 1300,
            borderRadius: 0,
            borderLeft: '1px solid var(--border)',
            bgcolor: 'var(--bg-primary)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Resize handle */}
          <Box
            onMouseDown={startDockResize}
            sx={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: '6px',
              cursor: 'col-resize',
              zIndex: 2,
              '&:hover': { bgcolor: 'var(--accent)', opacity: 0.4 },
            }}
          />
          {renderHeader(true)}
          {renderBody(true)}
        </Paper>
      )}

      {/* FAB */}
      {showFab && (
        <Fab
          onMouseDown={handleFabMouseDown}
          onClick={handleFabClick}
          data-tour-target="chatbot-fab"
          sx={{
            position: 'fixed',
            bottom: fabPos.bottom,
            right: fabPos.right,
            zIndex: 1300,
            bgcolor: '#8b5cf6',
            color: '#fff',
            cursor: 'grab',
            '&:active': { cursor: 'grabbing' },
            '&:hover': { bgcolor: '#7c3aed' },
          }}
        >
          <Box
            sx={{
              '@keyframes laPhysicsSwing': {
                '0%,100%': { transform: 'rotate(-25deg)' },
                '50%': { transform: 'rotate(25deg)' },
              },
              '@keyframes laPhysicsRotate': {
                from: { transform: 'rotate(0deg)' },
                to: { transform: 'rotate(360deg)' },
              },
              '@keyframes laPhysicsBob': {
                '0%,100%': { transform: 'translateY(0)' },
                '50%': { transform: 'translateY(-5px)' },
              },
              '@keyframes laPhysicsJitter': {
                '0%,100%': { transform: 'translate(0,0)' },
                '25%': { transform: 'translate(-2px,1px)' },
                '50%': { transform: 'translate(2px,-1px)' },
                '75%': { transform: 'translate(-1px,2px)' },
              },
              '@keyframes laPhysicsBreathe': {
                '0%,100%': { transform: 'scale(1)' },
                '50%': { transform: 'scale(1.2)' },
              },
              '@keyframes laPhysicsPiPulse': {
                '0%,100%': { transform: 'scale(1)' },
                '50%': { transform: 'scale(1.45)' },
              },
              display: 'flex',
              transformOrigin: 'center',
              animation: (() => {
                if (piPulse) return 'laPhysicsPiPulse 2s ease-in-out 5';
                if (isIdle) {
                  const { anim, duration, easing } = getIdleAnimation(getSelectedIconName());
                  return `${anim} ${duration} ${easing} infinite`;
                }
                return 'none';
              })(),
            }}
          >
            <PhysicsIcon size={30} />
          </Box>
        </Fab>
      )}
    </>
  );
}
