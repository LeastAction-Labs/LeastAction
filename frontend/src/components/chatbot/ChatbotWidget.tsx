/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CloseIcon from '@mui/icons-material/Close';
import CloseFullscreenIcon from '@mui/icons-material/CloseFullscreen';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import MenuIcon from '@mui/icons-material/Menu';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import RemoveIcon from '@mui/icons-material/Remove';
import { Box, Fab, IconButton, Paper, Typography } from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
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

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [expanded, setExpanded] = useState(false);
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
    if (open && !minimized) {
      setMinimized(true);
    } else {
      setOpen(true);
      setMinimized(false);
    }
  };

  const width = minimized ? 400 : expanded ? BASE_WIDTH * 2 : BASE_WIDTH;
  const height = minimized ? 'auto' : expanded ? Math.round(BASE_HEIGHT * 1.6) : BASE_HEIGHT;

  return (
    <>
      {/* Dialog */}
      {open && (
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
          {/* Header */}
          <Box
            sx={{
              px: 2,
              py: 1.5,
              bgcolor: 'var(--bg-secondary)',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            {!minimized && (
              <IconButton
                size="small"
                onClick={() => setMenuOpen((m) => !m)}
                sx={{ color: 'var(--text-secondary)', p: 0.5 }}
                title="Menu"
              >
                <MenuIcon sx={{ fontSize: 20 }} />
              </IconButton>
            )}
            {view === 'agent' && !isBusinessPreconfig && (
              <IconButton
                size="small"
                onClick={handleBack}
                sx={{ color: 'var(--text-secondary)', p: 0.5 }}
              >
                <ArrowBackIcon sx={{ fontSize: 18 }} />
              </IconButton>
            )}
            <PhysicsIcon size={20} />
            <Typography
              sx={{
                flex: 1,
                fontSize: FONT_SIZES.SM,
                fontWeight: FONT_WEIGHTS.WEIGHT_500,
                color: 'var(--text-primary)',
              }}
            >
              {view === 'select' ? 'Choose AI Agent' : providerConfig?.aiChatName}
            </Typography>
            <IconButton
              size="small"
              onClick={() =>
                (window.location.href =
                  '/path?itemtype=doc.file&itemname=AI%20Tech%20Intro&laui=getting-started-AI_tech_intro')
              }
              sx={{ color: 'var(--text-secondary)', p: 0.5 }}
              title="AI Tech Intro"
            >
              <HelpOutlineIcon sx={{ fontSize: 16 }} />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => setExpanded((e) => !e)}
              sx={{ color: 'var(--text-secondary)', p: 0.5 }}
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
              sx={{ color: 'var(--text-secondary)', p: 0.5 }}
              title={minimized ? 'Restore' : 'Minimize'}
            >
              <RemoveIcon sx={{ fontSize: 18 }} />
            </IconButton>
            <IconButton
              size="small"
              onClick={handleClose}
              sx={{ color: 'var(--text-secondary)', p: 0.5 }}
            >
              <CloseIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>

          {/* Body — display:none when minimized so components stay mounted and keep state */}
          <Box
            sx={{
              display: minimized ? 'none' : 'flex',
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
        </Paper>
      )}

      {/* FAB */}
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
    </>
  );
}
