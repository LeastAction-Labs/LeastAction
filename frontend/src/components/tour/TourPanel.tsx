/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import CloseIcon from '@mui/icons-material/Close';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  LinearProgress,
  Paper,
  Typography,
} from '@mui/material';

import { AI_CARDS, DOC_LINKS, LANDING_SUBTITLE, TASK_OPTIONS } from '@/config/tours';
import { useGlobal } from '@/contexts/GlobalContext';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';
import { useTour } from '@/contexts/TourContext';
import { getChildCatalogNodesByType, searchCatalogItems } from '@/services/catalog.service';

export default function TourPanel() {
  const {
    activeTour,
    currentStepIndex,
    isNavigating,
    showLanding,
    endTour,
    setCurrentStepIndex,
    setIsNavigating,
    startTour,
    closeLanding,
  } = useTour();
  const { currentProjectLaui } = useGlobal();
  const { setTaskModalState } = useTaskModalContext();
  const navigate = useNavigate();
  const [copied, setCopied] = useState(false);
  const [itemOpening, setItemOpening] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showLanding || activeTour) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        closeLanding();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showLanding, activeTour]);

  const handleOpenSuggestedItem = async (
    itemType: string,
    itemName: string,
    filterType?: string,
  ) => {
    setItemOpening(true);
    try {
      const result = await searchCatalogItems(undefined, false, {
        filters: { item_type: itemType, name: itemName },
        perPage: 1,
        projection: ['name', 'item_type', 'laui', '_laui'],
      });
      const item = result?.items?.[0]?.item ?? result?.items?.[0];
      if (!item) return;
      const laui = (item._laui ?? item.laui ?? item.id) as string;
      const itemtype = (item.item_type ?? itemType) as string;
      const itemname = (item.name ?? itemName) as string;
      await navigate({
        to: '/path',
        search: {
          laui,
          itemtype,
          itemname,
          ...(filterType ? { filtertype: filterType } : {}),
        },
      });
    } catch (e) {
      console.error('Tour item lookup failed', e);
    } finally {
      setItemOpening(false);
    }
  };

  const step = activeTour?.steps[currentStepIndex];
  const isLast = activeTour ? currentStepIndex === activeTour.steps.length - 1 : false;
  const isFirst = currentStepIndex === 0;

  useEffect(() => {
    if (!step?.autoClick || !step?.highlightTarget) return;
    const delay = step.autoClickDelay ?? 500;
    const timer = setTimeout(() => {
      const el = document.querySelector(`[data-tour-target="${step.highlightTarget}"]`);
      el?.click();
    }, delay);
    return () => clearTimeout(timer);
  }, [currentStepIndex, step?.autoClick, step?.highlightTarget, step?.autoClickDelay]);

  useEffect(() => {
    if (!step?.highlightTarget) return;
    const el = document.querySelector(`[data-tour-target="${step.highlightTarget}"]`);
    if (!el) return;
    const prevBoxShadow = el.style.boxShadow;
    const prevTransition = el.style.transition;
    el.style.transition = 'box-shadow 0.2s';
    el.style.boxShadow = '0 0 0 3px rgba(220, 38, 38, 0.7)';
    return () => {
      el.style.boxShadow = prevBoxShadow;
      el.style.transition = prevTransition;
    };
  }, [currentStepIndex, step?.highlightTarget]);

  useEffect(() => {
    if (!step?.taskPrefill) return;
    const prefill = step.taskPrefill;
    const randomSuffix = String(Math.floor(1000 + Math.random() * 9000));
    const taskName = `${prefill.namePrefix}_${randomSuffix}`;

    const openPrefilled = async () => {
      const [opResult, connResult, wfResult] = await Promise.all([
        searchCatalogItems(undefined, false, {
          filters: { name: prefill.operatorName },
          perPage: 1,
          projection: ['name', 'item_type', 'laui', '_laui'],
        }),
        searchCatalogItems(undefined, false, {
          filters: { name: prefill.connectionName },
          perPage: 1,
          projection: ['name', 'item_type', 'laui', '_laui'],
        }),
        currentProjectLaui
          ? getChildCatalogNodesByType(currentProjectLaui, 'folder.workflow', 'view')
          : Promise.resolve(null),
      ]);

      const opItem = opResult?.items?.[0]?.item ?? opResult?.items?.[0];
      const connItem = connResult?.items?.[0]?.item ?? connResult?.items?.[0];
      const wfFolder = wfResult?.items?.[0]?.item;
      const operatorLaui = (opItem?._laui ?? opItem?.laui ?? opItem?.id) as string | undefined;
      const connectionLaui = (connItem?._laui ?? connItem?.laui ?? connItem?.id) as
        | string
        | undefined;
      const workflowLaui = wfFolder?.laui;

      setTaskModalState({
        isOpen: true,
        mode: TaskModalMode.CREATE,
        scope: { scopeType: TaskModalScopeType.TASK },
        initialTaskData: {
          name: taskName,
          payload: prefill.payload,
          ...(operatorLaui ? { operator_laui: operatorLaui } : {}),
          ...(connectionLaui ? { connection_laui: connectionLaui } : {}),
          ...(workflowLaui ? { workflow_laui: workflowLaui } : {}),
        },
        onSuccess: () => {
          setCurrentStepIndex(currentStepIndex + 1);
        },
      });
    };

    const timer = setTimeout(() => {
      void openPrefilled();
    }, 800);
    return () => clearTimeout(timer);
  }, [currentStepIndex]);

  const navigateToFolder = async (folderType: string, filterType?: string) => {
    if (!currentProjectLaui) return;
    try {
      const result = await getChildCatalogNodesByType(currentProjectLaui, folderType, 'view');
      const folder = result.items[0]?.item;
      if (folder) {
        await navigate({
          to: '/path',
          search: {
            laui: folder.laui,
            itemtype: folder.item_type ?? '',
            itemname: folder.name ?? '',
            ...(filterType ? { filtertype: filterType } : {}),
          },
        });
      }
    } catch (e) {
      console.error('Tour navigation failed', e);
    }
  };

  const handleNext = async () => {
    if (!activeTour) return;

    if (step?.submitOnNext) {
      const submitBtn = document.querySelector('[data-tour-target="task-modal-submit"]');
      submitBtn?.click();
      return;
    }

    const nextIndex = currentStepIndex + 1;
    if (nextIndex >= activeTour.steps.length) {
      if (step?.refreshWorkflowOnFinish) {
        const refreshBtn = document.querySelector('[data-tour-target="refresh-table-button"]');
        refreshBtn?.click();
      }
      endTour();
      return;
    }

    const nextStep = activeTour.steps[nextIndex];
    if (nextStep.suggestedItemType && nextStep.suggestedItemName) {
      setIsNavigating(true);
      try {
        await handleOpenSuggestedItem(
          nextStep.suggestedItemType,
          nextStep.suggestedItemName,
          nextStep.suggestedFilterType,
        );
      } finally {
        setIsNavigating(false);
      }
    } else if (nextStep.navigateToRoute) {
      await navigate({
        to: nextStep.navigateToRoute.to as '/',
        search: nextStep.navigateToRoute.search ?? {},
      });
    } else if (nextStep.navigateToFolderType && currentProjectLaui) {
      setIsNavigating(true);
      try {
        await navigateToFolder(nextStep.navigateToFolderType, nextStep.navigateFilterType);
      } finally {
        setIsNavigating(false);
      }
    }
    setCurrentStepIndex(nextIndex);
  };

  const handleBack = async () => {
    if (currentStepIndex <= 0) return;
    const prevIndex = currentStepIndex - 1;
    const prevStep = activeTour!.steps[prevIndex];
    if (prevStep.navigateToFolderType && currentProjectLaui) {
      try {
        await navigateToFolder(prevStep.navigateToFolderType, prevStep.navigateFilterType);
      } catch (e) {
        console.error('Tour back navigation failed', e);
      }
    }
    setCurrentStepIndex(prevIndex);
  };

  const handleCopy = (text: string) => {
    void navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenDoc = (laui: string, itemname: string) => {
    void navigate({ to: '/path', search: { laui, itemtype: 'doc.file', itemname } });
  };

  // Landing screen
  if (showLanding && !activeTour) {
    return (
      <Paper
        ref={panelRef}
        elevation={8}
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          width: 540,
          maxHeight: 'calc(100vh - 48px)',
          zIndex: 9999,
          p: 2.5,
          bgcolor: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRadius: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <Box sx={{ flex: 1, pr: 1 }}>
            <Typography
              variant="subtitle2"
              sx={{ fontWeight: 600, color: 'var(--text-primary)', mb: 0.5 }}
            >
              Getting Started Tour
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                display: 'block',
              }}
            >
              {LANDING_SUBTITLE}
            </Typography>
          </Box>
          <IconButton
            size="small"
            onClick={closeLanding}
            sx={{ color: 'var(--text-secondary)', p: 0.5, flexShrink: 0 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        {/* Top section: Tasks */}
        <Box>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 600,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              mb: 0.75,
              display: 'block',
            }}
          >
            First Task
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Box sx={{ flex: '0 0 140px' }}>
              <Typography
                variant="caption"
                sx={{
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  display: 'block',
                  mb: 0.4,
                }}
              >
                Create your first task
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: 'var(--text-secondary)',
                  fontSize: '0.7rem',
                  lineHeight: 1.4,
                }}
              >
                Pick a data source to get started with a pre-built use case.
              </Typography>
            </Box>
            <Box sx={{ flex: 1, position: 'relative' }}>
              <Box
                sx={{
                  maxHeight: 140,
                  overflowY: 'auto',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 0.5,
                  scrollbarWidth: 'thin',
                  scrollbarColor: 'var(--text-secondary) var(--border)',
                  '&::-webkit-scrollbar': { width: 4 },
                  '&::-webkit-scrollbar-track': {
                    background: 'var(--border)',
                    borderRadius: 2,
                  },
                  '&::-webkit-scrollbar-thumb': {
                    background: 'var(--text-secondary)',
                    borderRadius: 2,
                  },
                }}
              >
                {TASK_OPTIONS.map((opt) => (
                  <Box
                    key={opt.tourId}
                    onClick={() => startTour(opt.tourId)}
                    sx={{
                      px: 1.25,
                      py: 0.75,
                      cursor: 'pointer',
                      borderRadius: 1,
                      border: '1px solid var(--border)',
                      bgcolor: 'var(--bg-primary)',
                      '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                      transition: 'background-color 0.15s',
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        display: 'block',
                      }}
                    >
                      {opt.label}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: 'var(--text-secondary)',
                        fontSize: '0.7rem',
                      }}
                    >
                      {opt.description}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        </Box>

        {/* Middle section: AI */}
        <Box>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 600,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              mb: 0.75,
              display: 'block',
            }}
          >
            AI Tour
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
            {AI_CARDS.map((card) => (
              <Paper
                key={card.tourId}
                onClick={() => startTour(card.tourId)}
                sx={{
                  p: 1.25,
                  cursor: 'pointer',
                  border: '1px solid var(--border)',
                  bgcolor: 'var(--bg-primary)',
                  borderRadius: 1.5,
                  '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                  transition: 'background-color 0.15s',
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    display: 'block',
                    mb: 0.4,
                  }}
                >
                  {card.title}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    color: 'var(--text-secondary)',
                    fontSize: '0.7rem',
                    lineHeight: 1.3,
                  }}
                >
                  {card.description}
                </Typography>
              </Paper>
            ))}
          </Box>
        </Box>

        {/* Bottom section: Docs */}
        <Box>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 600,
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              mb: 0.75,
              display: 'block',
            }}
          >
            Docs
          </Typography>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
              maxHeight: 180,
              overflowY: 'auto',
            }}
          >
            {DOC_LINKS.map((doc) => (
              <Box
                key={doc.laui}
                onClick={() =>
                  void navigate({
                    to: '/path',
                    search: {
                      laui: doc.laui,
                      itemtype: 'doc.file',
                      itemname: doc.itemName,
                    },
                  })
                }
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  px: 1.25,
                  py: 0.75,
                  cursor: 'pointer',
                  borderRadius: 1,
                  border: '1px solid var(--border)',
                  bgcolor: 'var(--bg-primary)',
                  '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                  transition: 'background-color 0.15s',
                }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      display: 'block',
                    }}
                  >
                    {doc.label}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      color: 'var(--text-secondary)',
                      fontSize: '0.7rem',
                      lineHeight: 1.3,
                    }}
                  >
                    {doc.description}
                  </Typography>
                  {(doc.quickLinkAction || doc.quickLinkAction2) && (
                    <Box sx={{ display: 'flex', gap: 1.5, mt: 0.5 }}>
                      {doc.quickLinkAction && (
                        <Typography
                          variant="caption"
                          component="span"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (doc.quickLinkAction === 'navigate' && doc.quickLink) {
                              if (doc.quickLink.startsWith('/')) {
                                void navigate({
                                  to: doc.quickLink as any,
                                });
                              } else {
                                void navigateToFolder(doc.quickLink, doc.quickLinkFilter);
                              }
                            } else if (doc.quickLinkAction === 'open-chat') {
                              closeLanding();
                              setTimeout(() => {
                                const fab = document.querySelector(
                                  '[data-tour-target="chatbot-fab"]',
                                );
                                fab?.click();
                              }, 150);
                            } else if (doc.quickLinkAction === 'external' && doc.quickLink) {
                              window.open(doc.quickLink, '_blank', 'noopener,noreferrer');
                            }
                          }}
                          sx={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 0.25,
                            color: 'var(--accent)',
                            fontSize: '0.68rem',
                            cursor: 'pointer',
                            '&:hover': { textDecoration: 'underline' },
                          }}
                        >
                          {doc.quickLinkLabel}
                          <OpenInNewIcon sx={{ fontSize: 10 }} />
                        </Typography>
                      )}
                      {doc.quickLinkAction2 && (
                        <Typography
                          variant="caption"
                          component="span"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (doc.quickLinkAction2 === 'navigate' && doc.quickLink2) {
                              void navigate({ to: doc.quickLink2 as any });
                            } else if (doc.quickLinkAction2 === 'external' && doc.quickLink2) {
                              window.open(doc.quickLink2, '_blank', 'noopener,noreferrer');
                            }
                          }}
                          sx={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 0.25,
                            color: 'var(--accent)',
                            fontSize: '0.68rem',
                            cursor: 'pointer',
                            '&:hover': { textDecoration: 'underline' },
                          }}
                        >
                          {doc.quickLinkLabel2}
                          <OpenInNewIcon sx={{ fontSize: 10 }} />
                        </Typography>
                      )}
                    </Box>
                  )}
                </Box>
                <OpenInNewIcon
                  sx={{
                    fontSize: 14,
                    color: 'var(--text-secondary)',
                    flexShrink: 0,
                  }}
                />
              </Box>
            ))}
          </Box>
        </Box>
      </Paper>
    );
  }

  if (!activeTour || !step) return null;

  const progress = ((currentStepIndex + 1) / activeTour.steps.length) * 100;

  return (
    <Paper
      elevation={8}
      sx={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        width: 360,
        zIndex: 9999,
        p: 2.5,
        bgcolor: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 2,
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 1,
        }}
      >
        <Typography variant="caption" sx={{ color: 'var(--text-secondary)' }}>
          {activeTour.title} — Step {currentStepIndex + 1} of {activeTour.steps.length}
        </Typography>
        <IconButton size="small" onClick={endTour} sx={{ color: 'var(--text-secondary)', p: 0.5 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      {/* Progress */}
      <LinearProgress
        variant="determinate"
        value={progress}
        sx={{
          mb: 2,
          borderRadius: 1,
          bgcolor: 'var(--border)',
          '& .MuiLinearProgress-bar': { bgcolor: 'var(--text-primary)' },
        }}
      />

      {/* Content */}
      <Typography
        variant="subtitle2"
        sx={{ fontWeight: 600, mb: 0.75, color: 'var(--text-primary)' }}
      >
        {step.title}
      </Typography>
      <Typography variant="body2" sx={{ color: 'var(--text-secondary)', mb: 1.5, lineHeight: 1.5 }}>
        {step.description}
      </Typography>

      {/* Direct item open button */}
      {step.suggestedItemType && step.suggestedItemName && (
        <Box sx={{ mb: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() =>
              void handleOpenSuggestedItem(
                step.suggestedItemType!,
                step.suggestedItemName!,
                step.suggestedFilterType,
              )
            }
            disabled={itemOpening}
            startIcon={
              itemOpening ? <CircularProgress size={12} sx={{ color: 'inherit' }} /> : undefined
            }
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              '&:hover': { borderColor: 'var(--text-primary)' },
              '&.Mui-disabled': { opacity: 0.6 },
            }}
          >
            Open {step.suggestedItemName}
          </Button>
        </Box>
      )}

      {/* Copyable block */}
      {step.copyableBlock && (
        <Box sx={{ mb: 1.5, position: 'relative' }}>
          <Box
            sx={{
              bgcolor: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: 1,
              p: 1.5,
              fontFamily: 'monospace',
              fontSize: '0.7rem',
              color: 'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              pr: 4,
            }}
          >
            {step.copyableBlock}
          </Box>
          <IconButton
            size="small"
            onClick={() => handleCopy(step.copyableBlock!)}
            sx={{
              position: 'absolute',
              top: 4,
              right: 4,
              color: 'var(--text-secondary)',
              p: 0.5,
            }}
            title={copied ? 'Copied!' : 'Copy'}
          >
            <ContentCopyIcon sx={{ fontSize: 14 }} />
          </IconButton>
          {copied && (
            <Typography
              variant="caption"
              sx={{ color: 'var(--text-secondary)', mt: 0.5, display: 'block' }}
            >
              Copied!
            </Typography>
          )}
        </Box>
      )}

      {/* Internal page button */}
      {step.internalUrl && (
        <Box sx={{ mb: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
            onClick={() => void navigate({ to: step.internalUrl as '/' })}
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              '&:hover': { borderColor: 'var(--text-primary)' },
            }}
          >
            Open page
          </Button>
        </Box>
      )}

      {/* External URL button */}
      {step.externalUrl && (
        <Box sx={{ mb: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
            onClick={() => window.open(step.externalUrl, '_blank')}
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              '&:hover': { borderColor: 'var(--text-primary)' },
            }}
          >
            Download .mcp.json
          </Button>
        </Box>
      )}

      {/* Doc link button */}
      {step.docLaui && (
        <Box sx={{ mb: 1.5 }}>
          <Button
            size="small"
            variant="outlined"
            endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
            onClick={() => handleOpenDoc(step.docLaui!, step.docItemName ?? 'Guide')}
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              '&:hover': { borderColor: 'var(--text-primary)' },
            }}
          >
            Open guide
          </Button>
        </Box>
      )}

      {/* Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, alignItems: 'center' }}>
        <Button
          size="small"
          onClick={endTour}
          sx={{
            color: 'var(--text-secondary)',
            textTransform: 'none',
            fontSize: '0.75rem',
          }}
        >
          Dismiss
        </Button>
        {!isFirst && (
          <Button
            size="small"
            variant="outlined"
            onClick={() => void handleBack()}
            sx={{
              textTransform: 'none',
              fontSize: '0.75rem',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
              '&:hover': { borderColor: 'var(--text-primary)' },
            }}
          >
            Back
          </Button>
        )}
        <Button
          size="small"
          variant="contained"
          onClick={() => void handleNext()}
          disabled={isNavigating}
          startIcon={
            isNavigating ? <CircularProgress size={12} sx={{ color: 'inherit' }} /> : undefined
          }
          sx={{
            textTransform: 'none',
            fontSize: '0.75rem',
            bgcolor: 'var(--text-primary)',
            color: 'var(--bg-secondary)',
            '&:hover': { bgcolor: 'var(--bg-tertiary)', color: 'var(--text-primary)' },
            '&.Mui-disabled': { opacity: 0.6 },
          }}
        >
          {isLast ? 'Finish' : 'Next'}
        </Button>
      </Box>
    </Paper>
  );
}
