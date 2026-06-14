/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import Box from '@mui/material/Box';
import { RichTreeView } from '@mui/x-tree-view/RichTreeView';

import { CORE_BACKEND_URL } from '@/config/urls';
import { FONT_FAMILIES, FONT_SIZES, FONT_WEIGHTS, TRANSITIONS } from '@/constants';
import type {
  LogFileDetailsResponse,
  LogTreeItem,
  LogsApiItem,
  LogsListResponse,
} from '@/services/logs.types';
import { consumeSSE } from '@/services/sseHelper';

interface LogsExplorerProps {
  onItemClick?: (event: React.MouseEvent, item: LogTreeItem) => void;
  folderPath?: string;
  /**
   * Optional initial path to load immediately as the starting folder.
   * If provided, the component will render a single root node pointing to this
   * path and load its children on mount.
   */
  initialPath?: string;
  rootLabel?: string;
  /**
   * Base logs API endpoint relative to backend root.
   * Defaults to `/api/v1/logs`.
   */
  apiEndpoint?: string;
  refreshState?: boolean;
}

const DEFAULT_LOGS_API = '/api/v1/logs';

const normalizePath = (p: string) => p.replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');

function fetchListItemsSSE(url: string): Promise<LogsListResponse> {
  return new Promise((resolve, reject) => {
    let result: LogsListResponse | null = null;
    consumeSSE(url, {
      onEvent(type, data: any) {
        if (type === 'data') result = data as LogsListResponse;
        else if (type === 'error') reject(new Error(data?.message ?? 'List failed'));
      },
      onError: reject,
      onDone: () => resolve(result ?? { items: [], directory: '', total_count: 0 }),
    });
  });
}

function fetchFileSSE(url: string): Promise<LogFileDetailsResponse> {
  return new Promise((resolve, reject) => {
    let meta: Partial<LogFileDetailsResponse> = {};
    let content = '';
    consumeSSE(url, {
      onEvent(type, data: any) {
        if (type === 'metadata') meta = data as Partial<LogFileDetailsResponse>;
        else if (type === 'chunk' && data?.content) content += data.content;
        else if (type === 'error') reject(new Error(data?.message ?? 'File read failed'));
      },
      onError: reject,
      onDone: () => resolve({ ...meta, content } as LogFileDetailsResponse),
    });
  });
}

const LogsExplorer = ({
  onItemClick,
  folderPath = '',
  initialPath = '',
  rootLabel = 'Monitoring',
  apiEndpoint = DEFAULT_LOGS_API,
  refreshState,
}: LogsExplorerProps) => {
  const [treeItems, setTreeItems] = useState<LogTreeItem[]>([]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [isLoadingTree, setIsLoadingTree] = useState(true);
  const [loadedFolders, setLoadedFolders] = useState<Set<string>>(new Set());

  const [popupOpen, setPopupOpen] = useState(false);
  const [popupContent, setPopupContent] = useState<LogFileDetailsResponse | null>(null);

  const normalizedInitialPath = normalizePath(initialPath || '');
  const loadedFoldersRef = useRef<Set<string>>(new Set());

  const buildApiPath = useCallback(
    (path: string, operation: 'listItems' | 'file' = 'listItems') => {
      let fullPath = path;

      // If folderPath is provided and path doesn't start with it, combine them
      if (folderPath) {
        const normalizedFolderPath = normalizePath(folderPath);
        const normalizedPath = normalizePath(path);

        if (normalizedPath && !normalizedPath.startsWith(normalizedFolderPath)) {
          fullPath = normalizedFolderPath
            ? `${normalizedFolderPath}/${normalizedPath}`
            : normalizedPath;
        } else if (normalizedPath) {
          fullPath = normalizedPath;
        } else {
          fullPath = normalizedFolderPath;
        }
      } else {
        fullPath = normalizePath(path);
      }

      const endpointPath = apiEndpoint || DEFAULT_LOGS_API;
      // Resolve base URL from environment variables
      const apiBaseUrl = CORE_BACKEND_URL;
      let base = endpointPath;
      if (apiBaseUrl) {
        const trimmed = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
        base = `${trimmed}${endpointPath}`;
      }

      if (operation === 'listItems') {
        const pathSegment = fullPath || '.'; // use "." for root listing
        return `${base}/listItems/${pathSegment}`;
      }
      return fullPath ? `${base}/file/${fullPath}` : `${base}/file`;
    },
    [folderPath, apiEndpoint],
  );

  const findItem = useCallback((items: LogTreeItem[], id: string): LogTreeItem | null => {
    for (const item of items) {
      if (item.id === id) return item;
      if (item.children) {
        const found = findItem(item.children, id);
        if (found) return found;
      }
    }
    return null;
  }, []);

  const updateTreeItem = useCallback(
    (items: LogTreeItem[], targetId: string, updates: Partial<LogTreeItem>): LogTreeItem[] =>
      items.map((item) => {
        if (item.id === targetId) {
          return { ...item, ...updates };
        }
        if (item.children) {
          return {
            ...item,
            children: updateTreeItem(item.children, targetId, updates),
          };
        }
        return item;
      }),
    [],
  );

  const getFileDetails = async (filePath: string) => {
    try {
      const apiPath = buildApiPath(filePath, 'file');
      const response = await fetchFileSSE(apiPath);

      setPopupContent(response);
      setPopupOpen(true);

      return response;
    } catch (error) {
      console.error('Error getting file details:', error);
      return null;
    }
  };

  const handleClosePopup = () => {
    setPopupOpen(false);
    setPopupContent(null);
  };

  const createPlaceholder = (parentId: string, name: string, index: number): LogTreeItem => ({
    id: `${parentId}-folder-${name}-${index}-placeholder`,
    label: 'Loading...',
    item_type: 'placeholder',
    file_type: 'folder',
    originalId: 'placeholder',
    data: null,
    children: [],
    path: '',
    labelStyle: {
      fontFamily: FONT_FAMILIES.PRIMARY,
      fontSize: FONT_SIZES.SM,
      fontWeight: FONT_WEIGHTS.NORMAL,
      color: 'var(--text-primary)',
    },
  });

  const loadFolderContents = useCallback(
    async (folderId: string, item: LogTreeItem) => {
      if (loadedFoldersRef.current.has(folderId)) return;

      try {
        setTreeItems((prev) => updateTreeItem(prev, folderId, { isLoading: true }));

        const itemPath = item.path || '';
        const apiPath = buildApiPath(itemPath, 'listItems');

        const response = await fetchListItemsSSE(apiPath);

        if (response && response.items) {
          const childTreeData = response.items.map(
            (apiItem: LogsApiItem, index: number): LogTreeItem => {
              const muiItemType = apiItem.type === 'directory' ? 'folder' : 'file';

              const fullItemPath =
                apiItem.path || (itemPath ? `${itemPath}/${apiItem.name}` : apiItem.name);

              return {
                id: `${folderId}-${muiItemType}-${apiItem.name}-${index}`,
                label: apiItem.name,
                item_type: muiItemType,
                file_type: apiItem.type === 'file' ? 'log' : 'folder',
                originalId: apiItem.name,
                data: apiItem,
                children:
                  muiItemType === 'folder'
                    ? [createPlaceholder(folderId, apiItem.name, index)]
                    : [],
                size: apiItem.size,
                modified: apiItem.modified,
                path: fullItemPath,
                labelStyle: {
                  fontFamily: FONT_FAMILIES.PRIMARY,
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.NORMAL,
                  color: 'var(--text-primary)',
                },
              };
            },
          );

          childTreeData.sort((a, b) => b.label.localeCompare(a.label));

          setTreeItems((prev) =>
            updateTreeItem(prev, folderId, {
              children: childTreeData,
              isLoading: false,
            }),
          );

          setLoadedFolders((prev) => {
            const next = new Set(prev).add(folderId);
            loadedFoldersRef.current = next;
            return next;
          });
        } else {
          // Empty folder
          setTreeItems((prev) =>
            updateTreeItem(prev, folderId, {
              children: [],
              isLoading: false,
            }),
          );
          setLoadedFolders((prev) => {
            const next = new Set(prev).add(folderId);
            loadedFoldersRef.current = next;
            return next;
          });
        }
      } catch (error: any) {
        console.error(`Error loading folder contents for ${folderId}:`, error);
        // Handle 404 or other errors - show empty folder instead of staying in loading
        setTreeItems((prev) =>
          updateTreeItem(prev, folderId, {
            children: [],
            isLoading: false,
          }),
        );
        // Mark as loaded to prevent infinite retries
        setLoadedFolders((prev) => {
          const next = new Set(prev).add(folderId);
          loadedFoldersRef.current = next;
          return next;
        });
      }
    },
    [buildApiPath, updateTreeItem],
  );

  const handleClick = async (event: React.MouseEvent, itemId: string) => {
    const item = findItem(treeItems, itemId);
    if (item) {
      if (item.item_type === 'file' && item.path) {
        await getFileDetails(item.path);
      } else if (item.item_type === 'folder') {
        const isCurrentlyExpanded = expanded.includes(itemId);

        if (isCurrentlyExpanded) {
          setExpanded((prev) => prev.filter((id) => id !== itemId));
        } else {
          setExpanded((prev) => [...prev, itemId]);

          if (!loadedFolders.has(itemId)) {
            await loadFolderContents(itemId, item);
          }
        }
      }

      if (onItemClick) {
        onItemClick(event, item);
      }
    }
  };

  const handleExpandedItemsChange = async (_event: React.SyntheticEvent, itemIds: string[]) => {
    const newlyExpanded = itemIds.filter((id) => !expanded.includes(id));

    setExpanded(itemIds);

    for (const itemId of newlyExpanded) {
      const item = findItem(treeItems, itemId);

      if (item && item.item_type === 'folder' && !loadedFolders.has(itemId)) {
        await loadFolderContents(itemId, item);
      }
    }
  };

  const renderLogContent = useCallback((content: string) => {
    // Split content into individual log lines
    const lines = content.split('\n').filter((line) => line.trim());

    return lines.map((line, index) => {
      // Parse log line structure: TIMESTAMP - LOGGER_NAME - LEVEL - MESSAGE
      // Note: Logger name can contain hyphens, so we match until we find a log level
      const logMatch = line.match(
        /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+?) - (INFO|ERROR|WARNING|DEBUG) - (.+)$/,
      );

      if (!logMatch) {
        // If line doesn't match expected format, display as-is
        return (
          <Box
            key={index}
            sx={{
              fontFamily: 'monospace',
              fontSize: FONT_SIZES.SM,
              padding: 1,
              borderBottom: '1px solid var(--bg-tertiary)',
              color: 'var(--text-primary)',
            }}
          >
            {line}
          </Box>
        );
      }

      const [, timestamp, loggerName, level, message] = logMatch;

      // Try to parse message as JSON
      let jsonData = null;
      try {
        jsonData = JSON.parse(message);
      } catch {
        // Not JSON, treat as plain text
      }

      const levelColor =
        level === 'ERROR'
          ? 'var(--accent)'
          : level === 'WARNING'
            ? '#ff9800'
            : level === 'INFO'
              ? '#4caf50'
              : 'var(--text-secondary)';

      return (
        <Box
          key={index}
          sx={{
            borderBottom: '1px solid var(--bg-tertiary)',
            padding: 1.5,
            marginBottom: 1,
          }}
        >
          {/* Log Header */}
          <Box
            sx={{
              display: 'flex',
              gap: 1.5,
              marginBottom: 1,
              flexWrap: 'wrap',
              alignItems: 'center',
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: 'var(--text-secondary)',
                fontFamily: 'monospace',
                fontSize: FONT_SIZES.XS,
              }}
            >
              {timestamp}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: levelColor,
                fontWeight: FONT_WEIGHTS.BOLD,
                fontSize: FONT_SIZES.XS,
                padding: '2px 8px',
                backgroundColor: 'var(--bg-tertiary)',
                borderRadius: 1,
              }}
            >
              {level}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: 'var(--text-secondary)',
                fontFamily: 'monospace',
                fontSize: FONT_SIZES.XS,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '400px',
              }}
              title={loggerName}
            >
              {loggerName}
            </Typography>
          </Box>

          {/* Log Content */}
          {jsonData ? (
            <Box
              sx={{
                backgroundColor: 'var(--bg-primary)',
                padding: 1.5,
                borderRadius: 1,
                borderLeft: `3px solid ${levelColor}`,
              }}
            >
              {Object.entries(jsonData).map(([key, value]) => (
                <Box
                  key={key}
                  sx={{
                    marginBottom: 1,
                    display: 'flex',
                    gap: 1,
                  }}
                >
                  <Typography
                    variant="body2"
                    component="span"
                    sx={{
                      color: '#64b5f6',
                      fontWeight: FONT_WEIGHTS.BOLD,
                      fontFamily: 'monospace',
                      fontSize: FONT_SIZES.SM,
                      minWidth: '150px',
                    }}
                  >
                    {key}:
                  </Typography>
                  <Typography
                    variant="body2"
                    component="span"
                    sx={{
                      color: 'var(--text-primary)',
                      fontFamily: 'monospace',
                      fontSize: FONT_SIZES.SM,
                      wordBreak: 'break-word',
                      flex: 1,
                    }}
                  >
                    {typeof value === 'object' && value !== null
                      ? JSON.stringify(value, null, 2)
                      : String(value)}
                  </Typography>
                </Box>
              ))}
            </Box>
          ) : (
            <Box
              sx={{
                backgroundColor: 'var(--bg-primary)',
                padding: 1.5,
                borderRadius: 1,
                borderLeft: `3px solid ${levelColor}`,
                fontFamily: 'monospace',
                fontSize: FONT_SIZES.SM,
                color: 'var(--text-primary)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {message}
            </Box>
          )}
        </Box>
      );
    });
  }, []);

  useEffect(() => {
    const fetchRootFolders = async () => {
      try {
        setIsLoadingTree(true);
        // Reset state when initialPath changes to prevent stale data
        setTreeItems([]);
        setLoadedFolders(new Set());
        loadedFoldersRef.current = new Set();
        setExpanded([]);

        // If an initial path is provided, start from that folder directly.
        if (normalizedInitialPath) {
          const rootFolder: LogTreeItem = {
            id: 'root-initial',
            label: rootLabel,
            item_type: 'folder',
            file_type: 'folder',
            originalId: 'root',
            data: null,
            children: [createPlaceholder('root-initial', 'loading', 0)],
            path: normalizedInitialPath,
          };

          setTreeItems([rootFolder]);
          setLoadedFolders(() => {
            const next = new Set<string>(['root-initial']);
            loadedFoldersRef.current = next;
            return next;
          });
          setExpanded(['root-initial']);

          await loadFolderContents('root-initial', rootFolder);
          return;
        }

        const apiPath = buildApiPath('', 'listItems');
        const response = await fetchListItemsSSE(apiPath);

        if (response && response.items) {
          const rootTreeData = response.items.map(
            (item: LogsApiItem, index: number): LogTreeItem => {
              const muiItemType = item.type === 'directory' ? 'folder' : 'file';
              const itemPath = item.path || item.name;

              return {
                id: `root-${muiItemType}-${item.name}-${index}`,
                label: item.name,
                item_type: muiItemType,
                file_type: item.type === 'file' ? 'log' : 'folder',
                originalId: item.name,
                data: item,
                children:
                  muiItemType === 'folder' ? [createPlaceholder('root', item.name, index)] : [],
                size: item.size,
                modified: item.modified,
                path: itemPath,
                labelStyle: {
                  fontFamily: FONT_FAMILIES.PRIMARY,
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.NORMAL,
                  color: 'var(--text-primary)',
                },
              };
            },
          );

          const rootFolder: LogTreeItem = {
            id: 'root-parent',
            label: rootLabel,
            item_type: 'folder',
            file_type: 'folder',
            originalId: 'root',
            data: null,
            children: rootTreeData,
            path: folderPath,
          };

          setTreeItems([rootFolder]);
          setLoadedFolders(() => {
            const next = new Set<string>(['root-parent']);
            loadedFoldersRef.current = next;
            return next;
          });
        } else {
          console.warn('LogsExplorer: No items in response');
          setTreeItems([]);
        }
      } catch (error) {
        console.error('Error fetching root log items:', error);
        setTreeItems([]);
      } finally {
        setIsLoadingTree(false);
      }
    };

    void fetchRootFolders();
  }, [
    folderPath,
    rootLabel,
    apiEndpoint,
    refreshState,
    buildApiPath,
    normalizedInitialPath,
    loadFolderContents,
  ]);

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <Box
        sx={{
          width: '100%',
          maxWidth: '100%',
          '& .MuiTreeView-root': {
            width: '100%',
          },
          '& .MuiTreeItem-root': {},
        }}
      >
        {isLoadingTree ? (
          <Typography
            variant="body2"
            sx={{
              p: 2,
              color: 'var(--text-secondary)',
              fontSize: FONT_SIZES.BASE,
            }}
          >
            Loading folders...
          </Typography>
        ) : treeItems.length === 0 ? (
          <Typography
            variant="body2"
            sx={{
              p: 2,
              color: 'var(--text-secondary)',
              fontSize: FONT_SIZES.BASE,
            }}
          >
            No logs available
          </Typography>
        ) : (
          <RichTreeView
            items={treeItems}
            aria-label="Logs Explorer"
            onItemClick={(event, itemId) => void handleClick(event, itemId)}
            expandedItems={expanded}
            onExpandedItemsChange={(event, itemIds) =>
              void handleExpandedItemsChange(event, itemIds)
            }
            slotProps={{
              item: {
                sx: {
                  '& .MuiTreeItem-content': {
                    padding: '4px 8px',
                    minHeight: '32px',
                    transition: `background-color ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,
                    '&:hover': {
                      bgcolor: 'var(--bg-selected)',
                    },
                  },
                  '& .MuiTreeItem-label': {
                    fontSize: `${FONT_SIZES.BASE} !important`,
                    fontWeight: `${FONT_WEIGHTS.NORMAL} !important`,
                    color: 'var(--text-primary) !important',
                  },
                },
              },
            }}
          />
        )}

        <Dialog open={popupOpen} onClose={handleClosePopup} maxWidth="lg" fullWidth>
          <DialogTitle>{popupContent?.name || 'File Content'}</DialogTitle>
          <DialogContent>
            {popupContent?.content_error && (
              <div style={{ color: 'var(--accent)', marginBottom: '1rem' }}>
                Error: {popupContent.content_error}
              </div>
            )}
            {popupContent?.content_reason && (
              <div style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                {popupContent.content_reason}
              </div>
            )}
            {popupContent?.content && (
              <div className="log-content">{renderLogContent(popupContent.content)}</div>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClosePopup}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </div>
  );
};

export default LogsExplorer;
