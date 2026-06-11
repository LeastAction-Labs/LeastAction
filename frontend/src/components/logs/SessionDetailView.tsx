/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  GetApp as DownloadIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import {
  Box,
  CircularProgress,
  Collapse,
  IconButton,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';

import { COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { CATEGORY_LABELS } from '@/constants/logConstants';
import { buildLogApiUrl, consumeSSE } from '@/services/sseHelper';

import StreamLogViewer from './StreamLogViewer';

// ── Types ────────────────────────────────────────────────────────────────────

interface CategoryInfo {
  name: string;
  label: string;
  files: { name: string; path: string }[];
}

export interface SessionDetailViewProps {
  taskLaui?: string;
  sessionId: string;
  sessionDate: string; // YYYY-MM-DD — display + fallback partition date
  logicalDate?: string; // for TASK / ACTION / CELERY path partition
  startTime?: string; // ISO timestamp — for API path partition + date range
  showDatePicker?: boolean; // show API date range picker (default true)
  pollUntilStable?: boolean; // poll every 1 s, stop after 3 consecutive identical results
  actionFilter?: string; // pollUntilStable: pick the <name>.log file instead of the first one
  instanceIndex?: number; // pollUntilStable: show only the Nth invocation block within the action log
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const DATE_INPUT_STYLE: React.CSSProperties = {
  padding: '2px 6px',
  background: 'var(--bg-tertiary)',
  color: 'var(--text-primary)',
  border: '1px solid var(--border)',
  borderRadius: 4,
  fontSize: FONT_SIZES.XXS,
  outline: 'none',
  colorScheme: 'dark',
};

function extractDatePart(dateStr: string): string {
  return (dateStr || '').replace('T', ' ').split(' ')[0];
}

function extractYMD(dateStr: string) {
  const [y = '', m = '01', d = '01'] = extractDatePart(dateStr).split('-');
  return { y, m: m.padStart(2, '0'), d: d.padStart(2, '0') };
}

function datesInRange(from: string, to: string): string[] {
  const dates: string[] = [];
  const cur = new Date(from);
  const end = new Date(to);
  while (cur <= end) {
    dates.push(cur.toISOString().split('T')[0]);
    cur.setDate(cur.getDate() + 1);
  }
  return dates.slice(0, 7); // safety cap — 7 days max
}

/** List direct children of a folder. Resolves with empty array on error. */
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

/** Stream a file and return its lines. */
function fetchFileLines(path: string): Promise<string[]> {
  return new Promise((resolve) => {
    const lines: string[] = [];
    consumeSSE(buildLogApiUrl(`file/${path}`), {
      onEvent(type, data: any) {
        if (type === 'chunk' && data?.content) {
          lines.push(
            ...(data.content as string).split('\n').filter((l: string) => l.trim() !== ''),
          );
        }
      },
      onError: () => resolve(lines),
      onDone: () => resolve(lines),
    });
  });
}

/** Download all files across all categories for a session. */
async function downloadSession(sessionId: string, categories: CategoryInfo[]) {
  const parts: string[] = [];
  for (const cat of categories) {
    parts.push(`\n════ ${cat.label} ════\n`);
    for (const file of cat.files) {
      const lines = await fetchFileLines(file.path);
      if (lines.length > 0) {
        parts.push(`\n──── ${file.name} ────\n`);
        parts.push(lines.join('\n'));
      }
    }
  }
  const blob = new Blob([parts.join('\n')], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `session_${sessionId?.substring(0, 8) ?? 'unknown'}.log`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/**
 * List all category subfolders under `basePath` and collect .log files.
 * Returns entries grouped by category name.
 */
async function collectByCategory(
  basePath: string,
  filterCats?: Set<string>,
): Promise<Map<string, { name: string; path: string }[]>> {
  const result = new Map<string, { name: string; path: string }[]>();
  const folders = await fetchListItems(basePath);
  await Promise.all(
    folders.map(async (folder: any) => {
      // listItems returns type "directory" (not "folder")
      if (folder.type !== 'directory') return;
      const catName = (folder.name as string).replace(/^category=/, '');
      if (filterCats && !filterCats.has(catName)) return;
      const files = await fetchListItems(`${basePath}/${folder.name}`);
      const logFiles = files
        .filter((f: any) => f.type === 'file' && (f.name as string).endsWith('.log'))
        // Use the `path` field returned by listItems (already relative to logs root)
        .map((f: any) => ({ name: f.name as string, path: f.path as string }));
      if (logFiles.length > 0) result.set(catName, logFiles);
    }),
  );
  return result;
}

// ── Component ────────────────────────────────────────────────────────────────

export default function SessionDetailView({
  taskLaui,
  sessionId,
  sessionDate,
  logicalDate,
  startTime,
  showDatePicker = true,
  pollUntilStable = false,
  actionFilter,
  instanceIndex,
}: SessionDetailViewProps) {
  const today = new Date().toISOString().split('T')[0];
  const defaultApiDate = startTime ? extractDatePart(startTime) : sessionDate || today;

  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [selectedCategoryIdx, setSelectedCategoryIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  // API-only date range
  const [apiDateFrom, setApiDateFrom] = useState(defaultApiDate);
  const [apiDateTo, setApiDateTo] = useState(defaultApiDate);
  const [appliedApiFrom, setAppliedApiFrom] = useState(defaultApiDate);
  const [appliedApiTo, setAppliedApiTo] = useState(defaultApiDate);

  // Ref so loadAll can read the latest API dates without them being a dependency
  const latestApiDates = useRef({ from: appliedApiFrom, to: appliedApiTo });
  latestApiDates.current = { from: appliedApiFrom, to: appliedApiTo };

  // Polling state (used only when pollUntilStable=true)
  const pollCountRef = useRef(0);
  const prevSnapshotRef = useRef('');
  const pollingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track previous applied dates to detect real changes (avoids firing on mount / session change)
  const prevAppliedApiRef = useRef({ from: appliedApiFrom, to: appliedApiTo });

  // ── Full load: TASK + ACTION + CELERY + API — resets tab ─────────────────
  const loadAll = useCallback(async () => {
    setLoading(true);
    setCategories([]);
    setSelectedCategoryIdx(0);
    setExpandedFiles(new Set());

    const infos: CategoryInfo[] = [];
    function mergeInto(catMap: Map<string, { name: string; path: string }[]>) {
      for (const [catName, files] of catMap) {
        const existing = infos.find((i) => i.name === catName);
        if (existing) {
          for (const f of files) {
            if (!existing.files.some((ef) => ef.path === f.path)) existing.files.push(f);
          }
        } else {
          infos.push({
            name: catName,
            label: CATEGORY_LABELS[catName] ?? catName,
            files,
          });
        }
      }
    }

    try {
      const effectiveDate = logicalDate || sessionDate || new Date().toISOString().split('T')[0];
      {
        const tlaui = taskLaui || 'no-task-laui';
        const { y, m, d } = extractYMD(effectiveDate);
        mergeInto(
          await collectByCategory(
            `verbose=TASK/yyyy=${y}/mm=${m}/dd=${d}/task_laui=${tlaui}/session_id=${sessionId}`,
          ),
        );
      }
      {
        // Fetch all NON_TASK categories (CELERY, API, etc.) for the session date
        const { y, m, d } = extractYMD(effectiveDate);
        mergeInto(
          await collectByCategory(
            `verbose=NON_TASK/yyyy=${y}/mm=${m}/dd=${d}/session_id=${sessionId}`,
          ),
        );
      }
      // API — use ref so these dates aren't a dependency of this callback
      for (const dateStr of datesInRange(latestApiDates.current.from, latestApiDates.current.to)) {
        const { y, m, d } = extractYMD(dateStr);
        mergeInto(
          await collectByCategory(
            `verbose=NON_TASK/yyyy=${y}/mm=${m}/dd=${d}/session_id=${sessionId}`,
            new Set(['API']),
          ),
        );
      }
      if (!infos.find((i) => i.name === 'API')) {
        infos.push({ name: 'API', label: CATEGORY_LABELS['API'] ?? 'API', files: [] });
      }
      const LAST = new Set(['API', 'CELERY', 'API_TRACEBACK']);
      infos.sort((a, b) => (LAST.has(a.name) ? 1 : 0) - (LAST.has(b.name) ? 1 : 0));
      setCategories(infos);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [sessionId, taskLaui, logicalDate, sessionDate]);

  // ── API-only reload — updates just the API category, preserves tab ────────
  const reloadApiOnly = useCallback(async () => {
    setLoading(true);
    const apiFiles: { name: string; path: string }[] = [];
    try {
      for (const dateStr of datesInRange(appliedApiFrom, appliedApiTo)) {
        const { y, m, d } = extractYMD(dateStr);
        const catMap = await collectByCategory(
          `verbose=NON_TASK/yyyy=${y}/mm=${m}/dd=${d}/session_id=${sessionId}`,
          new Set(['API']),
        );
        for (const f of catMap.get('API') ?? []) {
          if (!apiFiles.some((ef) => ef.path === f.path)) apiFiles.push(f);
        }
      }
      setCategories((prev) => {
        const next = [...prev];
        const entry = {
          name: 'API',
          label: CATEGORY_LABELS['API'] ?? 'API',
          files: apiFiles,
        };
        const idx = next.findIndex((c) => c.name === 'API');
        if (idx >= 0) next[idx] = entry;
        else next.push(entry);
        return next;
      });
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [sessionId, appliedApiFrom, appliedApiTo]);

  // Full reload on session/task change — with optional polling
  useEffect(() => {
    if (!pollUntilStable) {
      void loadAll();
      return;
    }

    // Reset poll tracking
    pollCountRef.current = 0;
    prevSnapshotRef.current = '';
    let stopped = false;

    const tick = async () => {
      if (stopped) return;
      try {
        // Re-use loadAll's internal logic but capture the result for comparison
        const infos: CategoryInfo[] = [];
        function mergeInto(catMap: Map<string, { name: string; path: string }[]>) {
          for (const [catName, files] of catMap) {
            const existing = infos.find((i) => i.name === catName);
            if (existing) {
              for (const f of files) {
                if (!existing.files.some((ef) => ef.path === f.path)) existing.files.push(f);
              }
            } else {
              infos.push({
                name: catName,
                label: CATEGORY_LABELS[catName] ?? catName,
                files,
              });
            }
          }
        }
        const effectiveDate = logicalDate || sessionDate || new Date().toISOString().split('T')[0];
        const tlaui = taskLaui || 'no-task-laui';
        const { y, m, d } = extractYMD(effectiveDate);
        mergeInto(
          await collectByCategory(
            `verbose=TASK/yyyy=${y}/mm=${m}/dd=${d}/task_laui=${tlaui}/session_id=${sessionId}`,
          ),
        );
        mergeInto(
          await collectByCategory(
            `verbose=NON_TASK/yyyy=${y}/mm=${m}/dd=${d}/session_id=${sessionId}`,
          ),
        );
        for (const dateStr of datesInRange(
          latestApiDates.current.from,
          latestApiDates.current.to,
        )) {
          const { y: ay, m: am, d: ad } = extractYMD(dateStr);
          mergeInto(
            await collectByCategory(
              `verbose=NON_TASK/yyyy=${ay}/mm=${am}/dd=${ad}/session_id=${sessionId}`,
              new Set(['API']),
            ),
          );
        }
        if (!infos.find((i) => i.name === 'API')) {
          infos.push({ name: 'API', label: CATEGORY_LABELS['API'] ?? 'API', files: [] });
        }
        const LAST = new Set(['API', 'CELERY', 'API_TRACEBACK']);
        infos.sort((a, b) => (LAST.has(a.name) ? 1 : 0) - (LAST.has(b.name) ? 1 : 0));

        if (stopped) return;

        const snapshot = JSON.stringify(
          infos
            .map((c) => ({ name: c.name, files: c.files.map((f) => f.path).sort() }))
            .sort((a, b) => a.name.localeCompare(b.name)),
        );

        if (snapshot !== prevSnapshotRef.current) {
          prevSnapshotRef.current = snapshot;
          pollCountRef.current = 1;
          setCategories(infos);
        } else {
          pollCountRef.current += 1;
        }

        if (!stopped && pollCountRef.current < 3) {
          pollingTimerRef.current = setTimeout(() => void tick(), 1000);
        }
      } catch {
        if (!stopped) pollingTimerRef.current = setTimeout(() => void tick(), 1000);
      }
    };

    void tick();

    return () => {
      stopped = true;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, [loadAll, pollUntilStable, sessionId, taskLaui, logicalDate, sessionDate]);

  // API-only reload — only when appliedApiFrom/To actually change (not on mount or session change)
  useEffect(() => {
    const prev = prevAppliedApiRef.current;
    const changed = prev.from !== appliedApiFrom || prev.to !== appliedApiTo;
    prevAppliedApiRef.current = { from: appliedApiFrom, to: appliedApiTo };
    if (!changed) return;
    void reloadApiOnly();
  }, [appliedApiFrom, appliedApiTo, reloadApiOnly]);

  const toggleFile = (path: string) => {
    setExpandedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleDownload = async () => {
    if (categories.length === 0 || downloading) return;
    setDownloading(true);
    try {
      await downloadSession(sessionId, categories);
    } finally {
      setDownloading(false);
    }
  };

  const currentCategory = categories[selectedCategoryIdx];

  // ── Render ──────────────────────────────────────────────────────────────

  // pollUntilStable mode: skip tabs/file-list, show StreamLogViewer directly
  if (pollUntilStable) {
    const SKIP = new Set(['API', 'CELERY', 'API_TRACEBACK']);
    const candidateFiles = categories.filter((c) => !SKIP.has(c.name)).flatMap((c) => c.files);
    const primaryFile = actionFilter
      ? (candidateFiles.find((f) => f.name === `${actionFilter}.log` || f.name === actionFilter) ??
        null)
      : (candidateFiles[0] ?? null);

    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        {primaryFile ? (
          <StreamLogViewer
            logFileUrl={`file/${primaryFile.path}`}
            title=""
            showHeader={false}
            showSearch
            showLevelFilter
            showDownload={false}
            enablePolling
            pollingInterval={1000}
            maxHeight="100%"
            sliceByMarker={
              typeof instanceIndex === 'number'
                ? {
                    marker: 'Received action execution request :',
                    index: instanceIndex,
                  }
                : undefined
            }
          />
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, p: 2 }}>
            <CircularProgress size={14} sx={{ color: 'var(--text-secondary)' }} />
            <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
              Waiting for logs…
            </Typography>
          </Box>
        )}
      </Box>
    );
  }

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
        }}
      >
        <CircularProgress size={24} sx={{ color: 'var(--text-secondary)' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Session header */}
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

        {/* Refresh + download buttons */}
        <Box sx={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title="Refresh">
            <span>
              <IconButton
                size="small"
                onClick={() => void loadAll()}
                disabled={loading}
                sx={{
                  color: 'var(--text-secondary)',
                  '&:hover': { color: 'var(--text-primary)' },
                }}
              >
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </span>
          </Tooltip>
          {categories.length > 0 && (
            <Tooltip title="Download all session logs">
              <span>
                <IconButton
                  size="small"
                  onClick={() => void handleDownload()}
                  disabled={downloading}
                  sx={{
                    color: 'var(--text-secondary)',
                    '&:hover': { color: 'var(--text-primary)' },
                  }}
                >
                  {downloading ? (
                    <CircularProgress size={14} sx={{ color: 'var(--text-secondary)' }} />
                  ) : (
                    <DownloadIcon sx={{ fontSize: 16 }} />
                  )}
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Box>
      </Box>

      {/* Category tabs */}
      {categories.length > 0 && (
        <Tabs
          value={selectedCategoryIdx}
          onChange={(_, v) => setSelectedCategoryIdx(v)}
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
              label={cat.label}
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
      )}

      {/* API date range — only shown when API tab is active and showDatePicker is true */}
      {currentCategory?.name === 'API' && showDatePicker && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
            px: 2,
            py: 0.75,
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
            bgcolor: 'var(--bg-tertiary)',
          }}
        >
          <Typography
            sx={{
              fontSize: '0.65rem',
              color: 'var(--text-secondary)',
              whiteSpace: 'nowrap',
            }}
          >
            Date range:
          </Typography>
          <input
            type="date"
            value={apiDateFrom}
            max={apiDateTo}
            onChange={(e) => setApiDateFrom(e.target.value)}
            style={DATE_INPUT_STYLE}
          />
          <Typography sx={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>–</Typography>
          <input
            type="date"
            value={apiDateTo}
            min={apiDateFrom}
            onChange={(e) => {
              const val = e.target.value;
              setApiDateTo(val);
              setAppliedApiFrom(apiDateFrom);
              setAppliedApiTo(val);
            }}
            style={DATE_INPUT_STYLE}
          />
        </Box>
      )}

      {/* Content */}
      <Box sx={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {!currentCategory ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
              No log categories found for this session
            </Typography>
          </Box>
        ) : currentCategory.files.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
              No logs found
            </Typography>
          </Box>
        ) : currentCategory.files.length === 1 ? (
          /* Single file — render directly */
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <StreamLogViewer
              logFileUrl={`file/${currentCategory.files[0].path}`}
              title={currentCategory.files[0].name}
              showHeader
              showSearch
              showLevelFilter
              showDownload={false}
              maxHeight="100%"
              paginated
              pageSize={100}
            />
          </Box>
        ) : (
          /* Multiple files — collapsible sections */
          currentCategory.files.map((file) => {
            const isExpanded = expandedFiles.has(file.path);
            return (
              <Box key={file.path}>
                <Box
                  onClick={() => toggleFile(file.path)}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    px: 2,
                    py: 1,
                    cursor: 'pointer',
                    borderBottom: '1px solid var(--border)',
                    '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                  }}
                >
                  {isExpanded ? (
                    <ExpandLessIcon sx={{ fontSize: 16, color: 'var(--text-secondary)' }} />
                  ) : (
                    <ExpandMoreIcon sx={{ fontSize: 16, color: 'var(--text-secondary)' }} />
                  )}
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      fontWeight: FONT_WEIGHTS.WEIGHT_600,
                      color: 'var(--text-primary)',
                      fontFamily: 'monospace',
                    }}
                  >
                    {file.name}
                  </Typography>
                </Box>
                <Collapse in={isExpanded}>
                  <Box sx={{ maxHeight: 500 }}>
                    <StreamLogViewer
                      logFileUrl={`file/${file.path}`}
                      title={file.name}
                      showHeader
                      showSearch
                      showLevelFilter
                      showDownload={false}
                      maxHeight={480}
                      paginated
                      pageSize={100}
                    />
                  </Box>
                </Collapse>
              </Box>
            );
          })
        )}
      </Box>
    </Box>
  );
}
