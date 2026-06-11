/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';

import {
  GetApp as DownloadIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  InputAdornment,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';

import { COLORS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import {
  LOG_LEVELS,
  LOG_LEVEL_COLORS,
  type LogLevel,
  type ParsedLogLine,
  parseLogLine,
} from '@/constants/logConstants';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { buildLogApiUrl, consumeSSE } from '@/services/sseHelper';
import { formatDateTimeFull, getTimeZoneLabel } from '@/utils/timeFormat';

// ── Props ────────────────────────────────────────────────────────────────────

export interface StreamLogViewerProps {
  /** Full SSE URL for the /file/ endpoint, OR a relative path (appended to log API base). */
  logFileUrl: string;
  title?: string;
  showSearch?: boolean;
  showLevelFilter?: boolean;
  showHeader?: boolean;
  showDownload?: boolean;
  maxHeight?: string | number;
  enablePolling?: boolean;
  pollingInterval?: number;
  onRefresh?: () => void;
  /**
   * When true, fetches the tail of the file (last `pageSize` lines) in chronological
   * order. Latest logs appear at the bottom. Scrolling to the top reveals a
   * "Load more" button to page backward through the file.
   */
  paginated?: boolean;
  /** Lines per page when paginated=true (default 400) */
  pageSize?: number;
  sliceByMarker?: { marker: string; index: number };
}

// ── Component ────────────────────────────────────────────────────────────────

export default function StreamLogViewer({
  logFileUrl,
  title,
  showSearch = true,
  showLevelFilter = true,
  showHeader = true,
  showDownload = true,
  maxHeight = '100%',
  enablePolling = false,
  pollingInterval = 5000,
  onRefresh,
  paginated = false,
  pageSize = 400,
  sliceByMarker,
}: StreamLogViewerProps) {
  const { timeZone } = useTimeFormat();
  const tzLabel = timeZone === 'utc' ? 'UTC' : getTimeZoneLabel();
  const [lines, setLines] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<LogLevel>('ALL');
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);

  // Paginated mode state
  const [hasMore, setHasMore] = useState(false);
  const [currentSkip, setCurrentSkip] = useState(0);
  const [isAtTop, setIsAtTop] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const loadMoreControllerRef = useRef<AbortController | null>(null);
  /** Snapshot of scrollHeight taken just before prepending older lines */
  const prevScrollHeightRef = useRef<number | null>(null);

  // ── Build URL ──────────────────────────────────────────────────────────────

  const buildUrl = useCallback(
    (skip: number) => {
      const base = logFileUrl.startsWith('http') ? logFileUrl : buildLogApiUrl(logFileUrl);
      if (!paginated) return base;
      const sep = base.includes('?') ? '&' : '?';
      return `${base}${sep}reverse=true&skip=${skip}&limit=${pageSize}`;
    },
    [logFileUrl, paginated, pageSize],
  );

  // ── Initial fetch ──────────────────────────────────────────────────────────

  const fetchLogs = useCallback(() => {
    controllerRef.current?.abort();
    setLoading(true);
    setError(null);
    setHasMore(false);
    setCurrentSkip(0);

    const accumulated: string[] = [];
    const url = buildUrl(0);

    const ctrl = consumeSSE(url, {
      onEvent(type, data: any) {
        if (type === 'chunk' && data?.content) {
          const newLines = data.content.split('\n').filter((l: string) => l.trim() !== '');
          accumulated.push(...newLines);
          if (data.has_more !== undefined) setHasMore(data.has_more);
          setLines([...accumulated]);
        } else if (type === 'error') {
          const msg: string = data?.message ?? 'Unknown error';
          if (!msg.includes('404')) setError(msg);
        }
      },
      onError(err) {
        if (!err.message.includes('404')) setError(err.message);
        setLoading(false);
      },
      onDone() {
        setLoading(false);
      },
    });

    controllerRef.current = ctrl;
  }, [buildUrl]);

  useEffect(() => {
    setLines([]);
    fetchLogs();
    return () => {
      controllerRef.current?.abort();
      loadMoreControllerRef.current?.abort();
    };
  }, [fetchLogs]);

  // Polling
  useEffect(() => {
    if (!enablePolling) return;
    const id = setInterval(fetchLogs, pollingInterval);
    return () => clearInterval(id);
  }, [enablePolling, pollingInterval, fetchLogs]);

  // Auto-load when user scrolls to top in paginated mode
  useEffect(() => {
    if (paginated && isAtTop && hasMore && !loadingMore && !loading) {
      handleLoadMore();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAtTop]);

  // ── Load more (paginated mode) — fetches older lines and prepends ──────────

  const handleLoadMore = useCallback(() => {
    if (loadingMore || !hasMore) return;

    loadMoreControllerRef.current?.abort();
    setLoadingMore(true);

    // Snapshot scroll height before DOM update so we can restore position
    prevScrollHeightRef.current = containerRef.current?.scrollHeight ?? null;

    const nextSkip = currentSkip + pageSize;
    const accumulated: string[] = [];
    const url = buildUrl(nextSkip);

    const ctrl = consumeSSE(url, {
      onEvent(type, data: any) {
        if (type === 'chunk' && data?.content) {
          const newLines = data.content.split('\n').filter((l: string) => l.trim() !== '');
          accumulated.push(...newLines);
          if (data.has_more !== undefined) setHasMore(data.has_more);
        } else if (type === 'error') {
          const msg: string = data?.message ?? 'Unknown error';
          if (!msg.includes('404')) setError(msg);
        }
      },
      onError(err) {
        if (!err.message.includes('404')) setError(err.message);
        setLoadingMore(false);
      },
      onDone() {
        setCurrentSkip(nextSkip);
        // Prepend older lines above existing (chronological order maintained)
        setLines((prev) => [...accumulated, ...prev]);
        setLoadingMore(false);
      },
    });

    loadMoreControllerRef.current = ctrl;
  }, [buildUrl, currentSkip, pageSize, hasMore, loadingMore]);

  // Restore scroll position after older lines are prepended at the top
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (prevScrollHeightRef.current !== null && el) {
      // Content was added at top: shift scrollTop by the added height
      el.scrollTop += el.scrollHeight - prevScrollHeightRef.current;
      prevScrollHeightRef.current = null;
    }
  }, [lines]);

  // ── Auto-scroll to bottom ─────────────────────────────────────────────────

  useEffect(() => {
    if (containerRef.current && !isUserScrolledUp) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines, isUserScrolledUp, selectedLevel, searchQuery]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsUserScrolledUp(distFromBottom > 40);
    if (paginated) {
      setIsAtTop(el.scrollTop < 40);
    }
  };

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
      setIsUserScrolledUp(false);
    }
  };

  // ── Filtering ─────────────────────────────────────────────────────────────

  const parsedLines = useMemo(() => {
    let lastLevel = '';
    return lines.map((raw) => {
      const parsed = parseLogLine(raw);
      if (parsed.level) lastLevel = parsed.level;
      return { raw, parsed, inheritedLevel: parsed.level || lastLevel };
    });
  }, [lines]);

  const { slicedParsedLines, sliceOutOfRange } = useMemo(() => {
    if (!sliceByMarker) return { slicedParsedLines: parsedLines, sliceOutOfRange: false };
    const { marker, index } = sliceByMarker;
    const starts: number[] = [];
    parsedLines.forEach((l, i) => {
      if (l.raw.includes(marker)) starts.push(i);
    });
    if (starts.length === 0 || index >= starts.length) {
      return { slicedParsedLines: [], sliceOutOfRange: true };
    }
    const from = starts[index];
    const to = starts[index + 1] ?? parsedLines.length;
    return { slicedParsedLines: parsedLines.slice(from, to), sliceOutOfRange: false };
  }, [parsedLines, sliceByMarker]);

  const filteredLines = useMemo(() => {
    return slicedParsedLines.filter(({ inheritedLevel, raw }) => {
      if (selectedLevel !== 'ALL' && inheritedLevel !== selectedLevel) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!raw.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [slicedParsedLines, selectedLevel, searchQuery]);

  // ── Render helpers ────────────────────────────────────────────────────────

  const renderRow = (parsed: ParsedLogLine, raw: string, inheritedLevel: string, idx: number) => {
    const effectiveLevel = parsed.level || inheritedLevel;
    const colors = LOG_LEVEL_COLORS[effectiveLevel];
    const levelColor = colors?.text ?? 'var(--text-primary)';
    const rowBg = colors?.bg ?? 'transparent';
    const rowTextColor =
      effectiveLevel && effectiveLevel !== 'INFO' ? levelColor : 'var(--text-secondary)';

    return (
      <Box
        key={idx}
        sx={{
          display: 'flex',
          gap: '12px',
          py: '2px',
          px: '10px',
          bgcolor: rowBg,
          '&:hover': { bgcolor: effectiveLevel ? rowBg : 'var(--bg-tertiary)' },
          fontFamily: 'monospace',
          fontSize: FONT_SIZES.XS,
          lineHeight: 1.5,
        }}
      >
        {/* Timestamp */}
        <Box
          sx={{
            color: rowTextColor,
            width: 170,
            minWidth: 58,
            maxWidth: 170,
            flexShrink: 0,
            overflow: 'hidden',
            whiteSpace: 'nowrap',
          }}
        >
          {parsed.date && parsed.time
            ? `${formatDateTimeFull(`${parsed.date}T${parsed.time}`)} ${tzLabel}`
            : `${parsed.date} ${parsed.time}${tzLabel}`}
        </Box>

        {/* Level */}
        {parsed.level && (
          <Box
            sx={{
              color: levelColor,
              fontWeight: FONT_WEIGHTS.WEIGHT_700,
              width: 52,
              minWidth: 52,
              maxWidth: 52,
              flexShrink: 0,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
            }}
          >
            {parsed.level}
          </Box>
        )}

        {/* Tag */}
        {parsed.tag && (
          <Box
            sx={{
              color: rowTextColor,
              width: 160,
              minWidth: 160,
              maxWidth: 160,
              flexShrink: 0,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            [{parsed.tag}]
          </Box>
        )}

        {/* Message */}
        <Box
          sx={{
            color: rowTextColor,
            flex: 1,
            minWidth: 0,
            whiteSpace: 'normal',
            wordBreak: 'break-word',
            overflowWrap: 'anywhere',
          }}
        >
          {parsed.level ? parsed.message : raw}
        </Box>
      </Box>
    );
  };

  // ── JSX ───────────────────────────────────────────────────────────────────

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: maxHeight,
        bgcolor: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 2,
        overflow: 'hidden',
        transition: 'background-color 0.3s ease, border-color 0.3s ease',
      }}
    >
      {/* Header */}
      {showHeader && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 1.5,
            borderBottom: '1px solid var(--border)',
            gap: 1,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {title && (
              <Typography
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                  color: 'var(--text-primary)',
                }}
              >
                {title}
              </Typography>
            )}
            {loading && <CircularProgress size={14} sx={{ color: 'var(--text-secondary)' }} />}
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {showSearch && (
              <TextField
                size="small"
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon
                          sx={{
                            fontSize: 16,
                            color: 'var(--text-secondary)',
                          }}
                        />
                      </InputAdornment>
                    ),
                  },
                }}
                sx={{
                  width: 200,
                  '& .MuiInputBase-root': {
                    fontSize: FONT_SIZES.XS,
                    height: 30,
                    bgcolor: 'var(--bg-tertiary)',
                  },
                  '& .MuiInputBase-input': {
                    py: 0.5,
                    px: 0.5,
                    color: 'var(--text-primary)',
                  },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                }}
              />
            )}
            {onRefresh && (
              <IconButton
                size="small"
                onClick={() => {
                  onRefresh();
                  fetchLogs();
                }}
                sx={{
                  color: 'var(--text-secondary)',
                  '&:hover': { color: 'var(--text-primary)' },
                }}
              >
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            )}
            {showDownload && (
              <IconButton
                size="small"
                onClick={() => {
                  const blob = new Blob([lines.join('\n')], {
                    type: 'text/plain',
                  });
                  const a = document.createElement('a');
                  a.href = URL.createObjectURL(blob);
                  a.download = title ?? 'logs.txt';
                  a.click();
                  URL.revokeObjectURL(a.href);
                }}
                sx={{
                  color: 'var(--text-secondary)',
                  '&:hover': { color: 'var(--text-primary)' },
                }}
              >
                <DownloadIcon sx={{ fontSize: 16 }} />
              </IconButton>
            )}
          </Box>
        </Box>
      )}

      {/* Level filter tabs */}
      {showLevelFilter && (
        <Tabs
          value={selectedLevel}
          onChange={(_, v) => setSelectedLevel(v)}
          sx={{
            minHeight: 34,
            borderBottom: '1px solid var(--border)',
            '& .MuiTabs-indicator': { backgroundColor: COLORS.GREEN },
          }}
        >
          {LOG_LEVELS.map((lvl) => {
            const dot = lvl !== 'ALL' ? LOG_LEVEL_COLORS[lvl]?.text : undefined;
            return (
              <Tab
                key={lvl}
                value={lvl}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    {dot && (
                      <Box
                        sx={{
                          width: 7,
                          height: 7,
                          borderRadius: '50%',
                          bgcolor: dot,
                          flexShrink: 0,
                        }}
                      />
                    )}
                    {lvl.charAt(0) + lvl.slice(1).toLowerCase()}
                  </Box>
                }
                sx={{
                  minHeight: 34,
                  minWidth: 64,
                  px: 1.5,
                  py: 0.5,
                  fontSize: FONT_SIZES.XS,
                  textTransform: 'none',
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                  color: 'var(--text-secondary)',
                  '&.Mui-selected': { color: COLORS.GREEN },
                }}
              />
            );
          })}
        </Tabs>
      )}

      {/* Log content */}
      {error ? (
        <Box sx={{ flex: 1, p: 3, textAlign: 'center' }}>
          <Typography sx={{ color: COLORS.RED, fontSize: FONT_SIZES.SM }}>{error}</Typography>
        </Box>
      ) : filteredLines.length === 0 && !loading ? (
        <Box
          sx={{
            flex: 1,
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {sliceOutOfRange ? (
            <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
              Waiting for logs…
            </Typography>
          ) : (
            <>
              <Typography
                sx={{
                  fontSize: FONT_SIZES.BASE,
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                  color: 'var(--text-primary)',
                  mb: 0.5,
                }}
              >
                {lines.length > 0 ? `No ${selectedLevel.toLowerCase()} logs` : 'No logs found'}
              </Typography>
              <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
                {lines.length > 0
                  ? 'No matching logs in this view.'
                  : 'Logs will appear here once available.'}
              </Typography>
            </>
          )}
        </Box>
      ) : (
        <Box sx={{ position: 'relative', flex: 1, minHeight: 0 }}>
          <Box ref={containerRef} onScroll={handleScroll} sx={{ height: '100%', overflow: 'auto' }}>
            {/* Auto-load sentinel — spinner while fetching older lines */}
            {paginated && hasMore && (loadingMore || isAtTop) && (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  py: 1,
                  borderBottom: '1px solid var(--border)',
                }}
              >
                <CircularProgress size={14} sx={{ color: 'var(--text-secondary)' }} />
              </Box>
            )}

            {filteredLines.map(({ parsed, raw, inheritedLevel }, i) =>
              renderRow(parsed, raw, inheritedLevel, i),
            )}
          </Box>

          {/* Jump to latest */}
          {isUserScrolledUp && (
            <Button
              onClick={scrollToBottom}
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 16,
                bgcolor: COLORS.GREEN,
                color: 'white',
                textTransform: 'none',
                fontSize: FONT_SIZES.XS,
                px: 1.5,
                py: 0.5,
                borderRadius: 1,
                minWidth: 'auto',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                '&:hover': { bgcolor: COLORS.GREEN_HOVER },
              }}
            >
              Jump to latest
            </Button>
          )}
        </Box>
      )}

      {/* Footer */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          px: 1.5,
          py: 0.75,
          borderTop: '1px solid var(--border)',
          bgcolor: 'var(--bg-tertiary)',
        }}
      >
        <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
          {selectedLevel === 'ALL'
            ? `${filteredLines.length} line${filteredLines.length !== 1 ? 's' : ''}`
            : `${filteredLines.length} of ${lines.length} lines`}
        </Typography>
        <Typography sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}>
          {loading
            ? 'Streaming...'
            : enablePolling
              ? `Polling every ${Math.floor(pollingInterval / 1000)}s`
              : ''}
        </Typography>
      </Box>
    </Box>
  );
}
