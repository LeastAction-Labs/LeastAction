/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';
import {
  Box,
  Chip,
  CircularProgress,
  ClickAwayListener,
  IconButton,
  Paper,
  TextField,
  Typography,
} from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES } from '@/constants';
import { useGlobal } from '@/contexts/GlobalContext';
import { createCatalogItem, searchCatalogItems } from '@/services';
import { chatWithAI } from '@/services/ai.service';

import ContentRenderer from './ContentRenderer';
import type { ProviderConfig } from './ProviderList';
import QuickTips from './QuickTips';

interface SkillItem {
  laui: string;
  name: string;
  description?: string;
  content?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  contentType?: string;
  timestamp: Date;
  toolCallsMade?: string[];
  isError?: boolean;
}

interface ChatPanelProps {
  providerConfig: ProviderConfig;
}

export default function ChatPanel({ providerConfig }: ChatPanelProps) {
  let { accountLaui } = useGlobal();
  if (!accountLaui) accountLaui = localStorage.getItem('la_account_laui');
  const [messages, setMessages] = useState<Message[]>(() =>
    (providerConfig.initialMessages ?? []).map((m, i) => ({
      id: `history-${i}`,
      role: m.role,
      content: m.content,
      timestamp: new Date(m.timestamp),
    })),
  );
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showTips, setShowTips] = useState(false);
  const [userFolderLaui, setUserFolderLaui] = useState<string | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<SkillItem[]>([]);
  const [allSkills, setAllSkills] = useState<SkillItem[]>([]);
  const [skillQuery, setSkillQuery] = useState('');
  const [skillDropdownOpen, setSkillDropdownOpen] = useState(false);
  const [skillsLoading, setSkillsLoading] = useState(true);
  const sessionNameRef = useRef<string | null>(null);
  const sessionLauiRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const autoSkillLauisRef = useRef<Set<string>>(new Set());
  const pendingSkillLauisRef = useRef<string[]>([]);

  useEffect(() => {
    const resolve = async () => {
      try {
        const response = await searchCatalogItems('folder.user', false, { perPage: 1 });
        const folder = response?.items?.[0];
        if (folder?.laui) setUserFolderLaui(folder.laui);
      } catch (err) {
        console.error('Failed to resolve user folder:', err);
      }
    };
    void resolve();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-select skills when report/folder context changes in Report Explorer.
  // Register the listener BEFORE announcing readiness, since ReportExplorer
  // re-dispatches synchronously in response to `la:chatpanel-ready`.
  useEffect(() => {
    const handler = (e: Event) => {
      const skillLauis = ((e as CustomEvent).detail?.skillLauis as string[]) ?? [];

      setSelectedSkills((prev) => {
        const userSkills = prev.filter((s) => !autoSkillLauisRef.current.has(s.laui));
        const resolved = skillLauis
          .map((laui) => allSkills.find((s) => s.laui === laui))
          .filter(Boolean) as SkillItem[];
        const toAdd = resolved.filter((s) => !userSkills.some((u) => u.laui === s.laui));
        autoSkillLauisRef.current = new Set(resolved.map((s) => s.laui));
        return [...toAdd, ...userSkills];
      });

      pendingSkillLauisRef.current = skillLauis.filter(
        (laui) => !allSkills.find((s) => s.laui === laui),
      );
    };
    window.addEventListener('la:report-skill', handler);
    window.dispatchEvent(new CustomEvent('la:chatpanel-ready'));
    return () => window.removeEventListener('la:report-skill', handler);
  }, [allSkills]);

  // Resolve pending skills once allSkills finishes loading
  useEffect(() => {
    if (!pendingSkillLauisRef.current.length || allSkills.length === 0) return;
    const resolved = pendingSkillLauisRef.current
      .map((laui) => allSkills.find((s) => s.laui === laui))
      .filter(Boolean) as SkillItem[];
    if (!resolved.length) return;
    setSelectedSkills((prev) => {
      const toAdd = resolved.filter((s) => !prev.some((e) => e.laui === s.laui));
      autoSkillLauisRef.current = new Set([
        ...autoSkillLauisRef.current,
        ...toAdd.map((s) => s.laui),
      ]);
      return [...toAdd, ...prev];
    });
    pendingSkillLauisRef.current = pendingSkillLauisRef.current.filter(
      (laui) => !resolved.some((s) => s.laui === laui),
    );
  }, [allSkills]);

  // Load all skills on mount
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const response = await searchCatalogItems('skill', false, {
          perPage: 50,
          projection: ['name', 'description', 'content'],
        });
        const items: SkillItem[] = (response?.items ?? []).map((raw: any) => {
          const item = raw.item || raw;
          return {
            laui: item._laui || item.laui,
            name: item.name || 'Unnamed Skill',
            description: item.description || item.data?.description || '',
            content: item.content || item.data?.content || '',
          };
        });
        setAllSkills(items);
      } catch (err) {
        console.error('Failed to load skills:', err);
      } finally {
        setSkillsLoading(false);
      }
    };
    void loadSkills();
  }, []);

  const filteredSkills = allSkills.filter(
    (s) => !skillQuery.trim() || s.name.toLowerCase().includes(skillQuery.toLowerCase()),
  );

  const buildSkillContent = useCallback(() => {
    if (selectedSkills.length === 0) return undefined;
    return selectedSkills
      .map((s) => s.content)
      .filter(Boolean)
      .join('\n\n');
  }, [selectedSkills]);

  const saveHistory = async (allMessages: Message[]) => {
    if (!userFolderLaui) return;
    if (!sessionNameRef.current) {
      sessionNameRef.current = `chat_session_${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}`;
    }
    try {
      const historyData: any = {
        item_type: 'chat_history',
        name: sessionNameRef.current,
        parent_laui: userFolderLaui,
        ...(accountLaui ? { account_laui: accountLaui } : {}),
        created_item_type: 'generate',
        ai_provider: providerConfig.aiProvider,
        chat_laui: providerConfig.aiChatLaui,
        ...(providerConfig.connectionLaui
          ? { connection_laui: providerConfig.connectionLaui }
          : {}),
        messages: allMessages.map((m) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        })),
      };
      const result = await createCatalogItem(historyData);
      if (!sessionLauiRef.current && result?.item_laui) {
        sessionLauiRef.current = result.item_laui;
      }
    } catch (err) {
      console.error('Failed to save chat history:', err);
    }
  };

  const handleCancel = () => {
    abortControllerRef.current?.abort();
  };

  const handleSend = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInputMessage('');
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    await saveHistory(updated);

    try {
      const historyMessages = updated.slice(-6).map((m) => ({ role: m.role, content: m.content }));
      const skillContent = buildSkillContent();
      const response = await chatWithAI(
        {
          prompt: inputMessage.trim(),
          chat_laui: providerConfig.aiChatLaui,
          messages: historyMessages,
          ...(providerConfig.connectionLaui
            ? { connection_laui: providerConfig.connectionLaui }
            : {}),
          ...(skillContent ? { skill_content: skillContent } : {}),
        },
        controller.signal,
      );

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message || 'No response',
        contentType: response.content_type || 'markdown',
        timestamp: new Date(),
        toolCallsMade: response.tool_calls_made,
      };
      const allMessages = [...updated, assistantMsg];
      setMessages(allMessages);
      await saveHistory(allMessages);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') return;
      const errorMsg: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content:
          error instanceof Error
            ? error.message
            : (error as any)?.message || String(error) || 'Failed to get response',
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      {/* Messages */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 1.5,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
        }}
      >
        {messages.length === 0 && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              flex: 1,
              gap: 2,
              px: 2,
            }}
          >
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.XS }}>
              Start a conversation with {providerConfig.aiChatName}
            </Typography>
            <QuickTips
              onSelect={(prompt) => {
                setInputMessage(prompt);
                setShowTips(false);
              }}
            />
          </Box>
        )}
        {messages.map((msg) => (
          <Box
            key={msg.id}
            sx={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.contentType && msg.contentType !== 'text' ? '100%' : '85%',
              px: 1.5,
              py: 1,
              borderRadius: BORDER_RADIUS.MD,
              bgcolor: msg.isError
                ? 'rgba(239, 68, 68, 0.08)'
                : msg.role === 'user'
                  ? 'var(--accent)'
                  : 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: msg.isError
                ? '1px solid rgba(239, 68, 68, 0.3)'
                : msg.role === 'assistant'
                  ? '1px solid var(--border)'
                  : 'none',
            }}
          >
            {msg.role === 'assistant' && (
              <Typography
                sx={{
                  fontSize: '10px',
                  color: msg.isError ? 'rgba(239,68,68,0.8)' : 'var(--text-secondary)',
                  mb: 0.5,
                  fontStyle: 'italic',
                }}
              >
                {msg.isError ? (
                  'error'
                ) : (
                  <>
                    {msg.toolCallsMade &&
                      msg.toolCallsMade.length > 0 &&
                      `Used: ${msg.toolCallsMade.join(', ')}  ·  `}
                    {msg.contentType ?? 'text'}
                  </>
                )}
              </Typography>
            )}
            <ContentRenderer
              content={msg.content}
              contentType={msg.role === 'user' ? 'text' : msg.contentType}
              showExpand={msg.role === 'assistant'}
            />
          </Box>
        ))}
        {isLoading && (
          <Box sx={{ alignSelf: 'flex-start', p: 1 }}>
            <CircularProgress size={18} sx={{ color: 'var(--accent)' }} />
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Box>

      {/* Quick tips panel (toggled by ? button) */}
      {showTips && messages.length > 0 && (
        <Box
          sx={{
            px: 1.5,
            pt: 1,
            pb: 0.5,
            borderTop: '1px solid var(--border)',
            bgcolor: 'var(--bg-primary)',
          }}
        >
          <QuickTips
            compact
            onSelect={(prompt) => {
              setInputMessage(prompt);
              setShowTips(false);
            }}
          />
        </Box>
      )}

      {/* Input */}
      <Box
        sx={{
          p: 1,
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: 0.5,
          alignItems: 'flex-end',
        }}
      >
        <TextField
          fullWidth
          size="small"
          multiline
          maxRows={8}
          placeholder="Type a message..."
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          disabled={isLoading}
          sx={{
            '& .MuiOutlinedInput-root': {
              fontSize: FONT_SIZES.XS,
              bgcolor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              borderRadius: BORDER_RADIUS.MD,
              '& fieldset': { borderColor: 'var(--border)' },
              '&:hover fieldset': { borderColor: 'var(--accent)' },
              '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
            },
            '& .MuiOutlinedInput-input': {
              color: 'var(--text-primary)',
            },
          }}
        />
        <IconButton
          onClick={() => setShowTips((p) => !p)}
          disabled={isLoading}
          sx={{
            color: showTips ? 'var(--accent)' : 'var(--text-secondary)',
            '&:hover': { color: 'var(--accent)' },
          }}
        >
          <HelpOutlineIcon sx={{ fontSize: 18 }} />
        </IconButton>
        {isLoading ? (
          <IconButton
            onClick={handleCancel}
            sx={{
              color: 'var(--text-secondary)',
              '&:hover': { color: 'var(--error, #f44336)' },
            }}
          >
            <StopIcon sx={{ fontSize: 20 }} />
          </IconButton>
        ) : (
          <IconButton
            onClick={() => void handleSend()}
            disabled={!inputMessage.trim()}
            sx={{
              color: 'var(--accent)',
              '&.Mui-disabled': { color: 'var(--text-secondary)' },
            }}
          >
            <SendIcon sx={{ fontSize: 20 }} />
          </IconButton>
        )}
      </Box>

      {/* Skill selector */}
      <Box sx={{ px: 1, pb: 0.75 }}>
        {selectedSkills.length > 0 && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 0.5 }}>
            {selectedSkills.map((skill) => (
              <Chip
                key={skill.laui}
                label={skill.name}
                size="small"
                icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
                onDelete={() =>
                  setSelectedSkills((prev) => prev.filter((s) => s.laui !== skill.laui))
                }
                disabled={isLoading}
                sx={{
                  fontSize: '11px',
                  height: 24,
                  bgcolor: 'var(--accent)',
                  color: '#fff',
                  '& .MuiChip-icon': { color: '#fff' },
                  '& .MuiChip-deleteIcon': {
                    color: 'rgba(255,255,255,0.7)',
                    '&:hover': { color: '#fff' },
                  },
                }}
              />
            ))}
          </Box>
        )}
        <ClickAwayListener onClickAway={() => setSkillDropdownOpen(false)}>
          <Box sx={{ position: 'relative' }}>
            <TextField
              fullWidth
              size="small"
              placeholder={
                skillsLoading ? 'Loading skills...' : `Search skills (${allSkills.length})...`
              }
              value={skillQuery}
              onChange={(e) => {
                setSkillQuery(e.target.value);
                setSkillDropdownOpen(true);
              }}
              onFocus={() => setSkillDropdownOpen(true)}
              disabled={isLoading || skillsLoading}
              InputProps={{
                startAdornment: (
                  <AutoAwesomeIcon
                    sx={{
                      fontSize: 16,
                      color: 'var(--text-secondary)',
                      mr: 0.5,
                    }}
                  />
                ),
                endAdornment: skillsLoading ? (
                  <CircularProgress size={14} sx={{ color: 'var(--accent)' }} />
                ) : null,
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  fontSize: '11px',
                  height: 30,
                  bgcolor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  borderRadius: BORDER_RADIUS.SM,
                  '& fieldset': { borderColor: 'var(--border)' },
                  '&:hover fieldset': { borderColor: 'var(--accent)' },
                  '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
                },
                '& .MuiOutlinedInput-input': {
                  color: 'var(--text-primary)',
                  py: 0.5,
                },
              }}
            />
            {skillDropdownOpen && filteredSkills.length > 0 && (
              <Paper
                elevation={4}
                sx={{
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  right: 0,
                  mb: 0.5,
                  maxHeight: 200,
                  overflow: 'auto',
                  zIndex: 10,
                  bgcolor: 'var(--bg-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: BORDER_RADIUS.SM,
                }}
              >
                {filteredSkills.map((skill) => {
                  const alreadySelected = selectedSkills.some((s) => s.laui === skill.laui);
                  return (
                    <Box
                      key={skill.laui}
                      onClick={() => {
                        if (!alreadySelected) {
                          setSelectedSkills((prev) => [...prev, skill]);
                          setSkillQuery('');
                          setSkillDropdownOpen(false);
                        }
                      }}
                      sx={{
                        px: 1.5,
                        py: 0.75,
                        cursor: alreadySelected ? 'default' : 'pointer',
                        opacity: alreadySelected ? 0.5 : 1,
                        '&:hover': {
                          bgcolor: alreadySelected ? 'transparent' : 'var(--bg-secondary)',
                        },
                        borderBottom: '1px solid var(--border)',
                        '&:last-child': { borderBottom: 'none' },
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.XS,
                          color: 'var(--text-primary)',
                          fontWeight: 500,
                        }}
                      >
                        {skill.name}
                      </Typography>
                      {skill.description && (
                        <Typography
                          sx={{
                            fontSize: '10px',
                            color: 'var(--text-secondary)',
                            mt: 0.25,
                          }}
                          noWrap
                        >
                          {skill.description}
                        </Typography>
                      )}
                    </Box>
                  );
                })}
              </Paper>
            )}
            {skillDropdownOpen && !skillsLoading && filteredSkills.length === 0 && (
              <Paper
                elevation={4}
                sx={{
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  right: 0,
                  mb: 0.5,
                  p: 1.5,
                  bgcolor: 'var(--bg-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: BORDER_RADIUS.SM,
                }}
              >
                <Typography
                  sx={{
                    fontSize: '11px',
                    color: 'var(--text-secondary)',
                    textAlign: 'center',
                  }}
                >
                  {allSkills.length === 0 ? 'No skills available' : 'No matching skills'}
                </Typography>
              </Paper>
            )}
          </Box>
        </ClickAwayListener>
      </Box>
    </Box>
  );
}
