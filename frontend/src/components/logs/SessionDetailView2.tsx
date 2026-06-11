/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { Refresh as RefreshIcon } from '@mui/icons-material';
import { Box, CircularProgress, IconButton, Tab, Tabs, Tooltip, Typography } from '@mui/material';

import { COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { CATEGORY_LABELS } from '@/constants/logConstants';
import { buildLogApiUrl, consumeSSE } from '@/services/sseHelper';

import StreamLogViewer from './StreamLogViewer2';

// ── Types ────────────────────────────────────────────────────────────────────

export interface SessionDetailViewProps {
  sessionId: string;
  sessionDate: string; // YYYY-MM-DD partition date
  pollUntilStable?: boolean; // poll structural paths for stabilization
}

interface CategoryState {
  name: string;
  filePaths: string[]; // 🛠️ Changed from filePath to an array
  resolved: boolean;
}

function extractYMD(dateStr: string) {
  const [y = '', m = '01', d = '01'] = (dateStr || '').split('-');
  return { y, m: m.padStart(2, '0'), d: d.padStart(2, '0') };
}

/** List direct children of a folder via SSE stream. */
function fetchListItems(folderPath: string): Promise<any[]> {
  return new Promise((resolve) => {
    const items: any[] = [];
    consumeSSE(buildLogApiUrl(`listItems/${folderPath}`), {
      onEvent(type, data: any) {
        if (type === 'data' && data?.items) items.push(...data.items);
      },
      onError: () => resolve(items),
      onDone: () => resolve(items),
    });
  });
}

/** 🛠️ Recursively crawls and collects ALL `.log` files in a directory tree */
async function findAllLogFiles(basePath: string): Promise<string[]> {
  const items = await fetchListItems(basePath);
  const paths: string[] = [];

  // Find all file types ending in .log at this current tier
  const logFiles = items.filter((i) => i.type === 'file' && i.name.endsWith('.log'));
  paths.push(...logFiles.map((f) => f.path));

  // Recurse directories deep down
  const subDirs = items.filter((i) => i.type === 'directory');
  for (const dir of subDirs) {
    const nestedPaths = await findAllLogFiles(`${basePath}/${dir.name}`);
    paths.push(...nestedPaths);
  }
  return paths;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function SessionDetailView({
  sessionId,
  sessionDate,
  pollUntilStable = true,
}: SessionDetailViewProps) {
  const { y, m, d } = extractYMD(sessionDate);
  const datePartition = `yyyy=${y}/mm=${m}/dd=${d}`;

  // Seeding local states tracking list profiles
  const [categories, setCategories] = useState<CategoryState[]>([
    { name: 'API', filePaths: [], resolved: false },
    { name: 'CELERY', filePaths: [], resolved: false },
    { name: 'KETO', filePaths: [], resolved: false },
    { name: 'API_TRACEBACK', filePaths: [], resolved: false },
  ]);

  const [selectedCategoryIdx, setSelectedCategoryIdx] = useState(0);
  const [resolvingPath, setResolvingPath] = useState(false);

  const pollingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Resolve All Log Paths On Demand ────────────────────────────────────────
  const resolveCategoryPaths = useCallback(
    async (catName: string): Promise<string[]> => {
      try {
        if (catName === 'API') {
          return await findAllLogFiles(
            `verbose=NON_TASK/${datePartition}/session_id=${sessionId}/category=API`,
          );
        }
        if (catName === 'CELERY') {
          return await findAllLogFiles(
            `verbose=NON_TASK/${datePartition}/session_id=${sessionId}/category=CELERY`,
          );
        }
        if (catName === 'API_TRACEBACK') {
          return await findAllLogFiles(
            `verbose=NON_TASK/${datePartition}/session_id=${sessionId}/category=API_TRACEBACK`,
          );
        }
        if (catName === 'KETO') {
          return await findAllLogFiles(
            `verbose=OTHER/${datePartition}/session_id=${sessionId}/category=KETO`,
          );
        }
      } catch (err) {
        console.error(`Error resolving path systems for ${catName}:`, err);
      }
      return [];
    },
    [sessionId, datePartition],
  );

  // Handle Tab Activation Resolution Flow Changes
  const handleTabChange = useCallback(
    async (index: number) => {
      setSelectedCategoryIdx(index);
      const targetCat = categories[index];

      if (!targetCat.resolved) {
        setResolvingPath(true);
        const paths = await resolveCategoryPaths(targetCat.name);
        setCategories((prev) => {
          const next = [...prev];
          next[index] = { ...next[index], filePaths: paths, resolved: true };
          return next;
        });
        setResolvingPath(false);
      }
    },
    [categories, resolveCategoryPaths],
  );

  // Trigger base load target immediately
  useEffect(() => {
    if (selectedCategoryIdx === 0 && !categories[0].resolved && !resolvingPath) {
      void handleTabChange(0);
    }
  }, [handleTabChange, selectedCategoryIdx, categories, resolvingPath]);

  // Background stability pipeline sync polling
  useEffect(() => {
    if (!pollUntilStable) return;

    let stopped = false;
    const tick = () => {
      if (stopped) return;

      setCategories((prev) => {
        const next = [...prev];
        void Promise.all(
          next.map(async (cat) => {
            if (!cat.resolved) {
              const paths = await resolveCategoryPaths(cat.name);
              if (paths.length > 0) {
                cat.filePaths = paths;
                cat.resolved = true;
              }
            }
          }),
        ).then(() => {
          if (!stopped) setCategories([...next]);
        });
        return prev;
      });

      if (!stopped) pollingTimerRef.current = setTimeout(() => tick(), 3000);
    };

    tick();
    return () => {
      stopped = true;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, [pollUntilStable, resolveCategoryPaths]);

  const currentCategory = categories[selectedCategoryIdx];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Session Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 2,
          py: 1.25,
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
          gap: 1,
        }}
      >
        <Typography
          sx={{
            fontSize: FONT_SIZES.SM,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-secondary)',
          }}
        >
          Session:
        </Typography>
        <Typography
          sx={{
            fontSize: FONT_SIZES.SM,
            fontWeight: FONT_WEIGHTS.WEIGHT_600,
            color: 'var(--text-primary)',
            fontFamily: 'monospace',
          }}
        >
          {sessionId?.substring(0, 8) ?? 'N/A'}…
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
          {sessionDate}
        </Typography>

        {/* Refresh button */}
        <Box sx={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title="Force Re-resolve Current Tab">
            <span>
              <IconButton
                size="small"
                onClick={() => {
                  void (async () => {
                    setResolvingPath(true);
                    const paths = await resolveCategoryPaths(currentCategory.name);
                    setCategories((prev) => {
                      const next = [...prev];
                      next[selectedCategoryIdx] = {
                        name: currentCategory.name,
                        filePaths: paths,
                        resolved: true,
                      };
                      return next;
                    });
                    setResolvingPath(false);
                  })();
                }}
                disabled={resolvingPath}
                sx={{
                  color: 'var(--text-secondary)',
                  '&:hover': { color: 'var(--text-primary)' },
                }}
              >
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>

      {/* Category Tabs Framework */}
      <Tabs
        value={selectedCategoryIdx}
        onChange={(_, v) => void handleTabChange(v)}
        sx={{
          minHeight: 36,
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
          '& .MuiTabs-indicator': { backgroundColor: COLORS.BLUE },
        }}
      >
        {categories.map((cat) => (
          <Tab
            key={cat.name}
            label={CATEGORY_LABELS[cat.name] ?? cat.name}
            sx={{
              minHeight: 36,
              minWidth: 70,
              px: 2,
              py: 0.5,
              fontSize: FONT_SIZES.XS,
              textTransform: 'none',
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
              color: 'var(--text-secondary)',
              '&.Mui-selected': { color: COLORS.BLUE },
            }}
          />
        ))}
      </Tabs>

      {/* Primary Log Content Viewer Window */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
          gap: currentCategory?.filePaths.length > 1 ? 2 : 0,
          p: currentCategory?.filePaths.length > 1 ? 2 : 0,
          bgcolor: currentCategory?.filePaths.length > 1 ? 'var(--bg-primary)' : 'transparent',
        }}
      >
        {resolvingPath ? (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
              gap: 1,
            }}
          >
            <CircularProgress size={16} sx={{ color: 'var(--text-secondary)' }} />
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.XS }}>
              Locating target log partitions...
            </Typography>
          </Box>
        ) : !currentCategory || currentCategory.filePaths.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
              No structural logs found inside the {currentCategory?.name} directory tree.
            </Typography>
          </Box>
        ) : (
          /* 🛠️ Map over every path file variant discovered in the collection */
          currentCategory.filePaths.map((path) => {
            const filename = path.split('/').pop() || 'log_stream.log';
            return (
              <Box
                sx={{
                  flex: currentCategory.filePaths.length > 1 ? '0 0 450px' : 1,
                  minHeight: 0,
                  display: 'flex',
                  flexDirection: 'column',
                }}
                key={path}
              >
                <StreamLogViewer
                  logFileUrl={`file/${path}`}
                  title={`${filename}`}
                  showHeader={currentCategory.filePaths.length > 1} // Only show the title panel inner frame if multi-file view is active
                  showSearch
                  showLevelFilter
                  showDownload={false}
                  maxHeight="100%"
                  paginated={true}
                  pageSize={50}
                />
              </Box>
            );
          })
        )}
      </Box>
    </Box>
  );
}
