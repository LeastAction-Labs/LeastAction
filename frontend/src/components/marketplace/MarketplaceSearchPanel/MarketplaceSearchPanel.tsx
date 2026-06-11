/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useRef } from 'react';

import { Download as ImportIcon } from '@mui/icons-material';
import SearchIcon from '@mui/icons-material/Search';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  Box,
  Chip,
  CircularProgress,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  Skeleton,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';
import { getCoreVersion } from '@/config/version';
import { useCatalog } from '@/contexts/CatalogContext';
import { getCatalogItemById } from '@/services';
import { schemaExists } from '@/services/schema.service';
import type { ParsedMarketplaceQuery } from '@/utils/marketplaceSearch';
import { removeFieldFilter } from '@/utils/marketplaceSearch';
import { compatibilityMessage, isCoreCompatible } from '@/utils/semver';

import LAMarketplaceIcon from '../LAMarketplaceIcon/LAMarketplaceIcon';

interface MarketplaceSearchPanelProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  parsedQuery: ParsedMarketplaceQuery;
  results: CatalogItem[];
  isLoading: boolean;
  isLoadingMore?: boolean;
  hasNextPage?: boolean;
  onLoadMore?: () => void;
  selectedLaui: string | null;
  onSelect: (item: CatalogItem) => void;
  width?: number;
}

export default function MarketplaceSearchPanel({
  searchQuery,
  onSearchChange,
  parsedQuery,
  results,
  isLoading,
  isLoadingMore = false,
  hasNextPage = false,
  onLoadMore,
  selectedLaui,
  onSelect,
  width = 320,
}: MarketplaceSearchPanelProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || !hasNextPage || isLoadingMore) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 600) {
      onLoadMore?.();
    }
  }, [hasNextPage, isLoadingMore, onLoadMore]);

  const handleImport = async (itemId: string) => {
    const itemData = await getCatalogItemById(itemId, true);
    setImportModalState({ isOpen: true, itemData });
  };

  const { setImportModalState } = useCatalog();
  const hasFilters = Object.keys(parsedQuery.fieldFilters).length > 0;

  return (
    <Box
      sx={{
        width,
        flexShrink: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRight: 1,
        borderColor: 'var(--border-color)',
        bgcolor: 'var(--bg-secondary)',
      }}
    >
      {/* Search input */}
      <Box
        sx={{
          p: 0.5,
          borderBottom: hasFilters ? 0 : 1,
          borderColor: 'var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        Marketplace
      </Box>

      {/* Search input */}
      <Box
        sx={{
          p: 0.5,
          borderBottom: hasFilters ? 0 : 1,
          borderColor: 'var(--border-color)',
        }}
      >
        <TextField
          fullWidth
          size="small"
          placeholder='Search… or use publisher:"name" tag:"x"'
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          autoFocus
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: 18, color: 'var(--text-secondary)' }} />
                </InputAdornment>
              ),
            },
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              fontSize: '13px',
              bgcolor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              '& fieldset': { borderColor: 'var(--border-color)' },
              '&:hover fieldset': { borderColor: 'var(--accent)' },
              '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
            },
            '& .MuiInputBase-input::placeholder': {
              color: 'var(--text-secondary)',
              opacity: 1,
            },
          }}
        />
      </Box>

      {/* Active filter chips */}
      {hasFilters && (
        <Box
          sx={{
            px: 1.5,
            py: 0.75,
            borderBottom: 1,
            borderColor: 'var(--border-color)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 0.5,
          }}
        >
          {Object.entries(parsedQuery.fieldFilters).flatMap(([field, values]) =>
            values.map((value) => (
              <Chip
                key={`${field}:${value}`}
                label={`${field}:"${value}"`}
                size="small"
                onDelete={() => onSearchChange(removeFieldFilter(searchQuery, field, value))}
                sx={{
                  fontSize: '11px',
                  bgcolor: 'var(--accent)',
                  color: '#fff',
                  '& .MuiChip-deleteIcon': { color: 'rgba(255,255,255,0.7)' },
                }}
              />
            )),
          )}
        </Box>
      )}

      {/* Results list */}
      <Box ref={listRef} onScroll={handleScroll} sx={{ flex: 1, overflow: 'auto' }}>
        {isLoading ? (
          <Box sx={{ p: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <Box key={i} sx={{ px: 1 }}>
                <Skeleton variant="text" width="70%" sx={{ bgcolor: 'var(--bg-primary)' }} />
                <Skeleton
                  variant="text"
                  width="40%"
                  height={16}
                  sx={{ bgcolor: 'var(--bg-primary)' }}
                />
              </Box>
            ))}
          </Box>
        ) : results.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              {searchQuery ? 'No results found' : 'No items available'}
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {results.map((item) => {
              const coreVersion = getCoreVersion();
              const incompatible = !isCoreCompatible(item.version_compatibility, coreVersion);
              const deprecated = !!item.version_details?.deprecated;
              const dimmed = incompatible || deprecated;
              const isSelected = selectedLaui === item.laui;

              const warningTip = incompatible
                ? (compatibilityMessage(item.version_compatibility, coreVersion) ??
                  'Incompatible core version')
                : deprecated
                  ? 'This item is deprecated'
                  : '';

              const isOfficial = item.publisher === 'LeastAction';
              const isVerified = !!item.verified && !isOfficial;

              const typeSupported = schemaExists(item.item_type);
              const showImport = typeSupported && !incompatible && !deprecated;

              const importBtn = showImport ? (
                <Tooltip title={`Import "${item.name}"`} placement="left">
                  <IconButton
                    size="small"
                    data-tour-target="marketplace-import-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleImport(item.laui);
                    }}
                    sx={{
                      flexShrink: 0,
                      color: isSelected ? '#fff' : 'var(--text-primary)',
                      p: 0.5,
                      '&:hover': { bgcolor: 'transparent' },
                    }}
                  >
                    <ImportIcon sx={{ fontSize: 16 }} />
                  </IconButton>
                </Tooltip>
              ) : null;

              return (
                <ListItemButton
                  key={item.laui}
                  selected={isSelected}
                  onClick={() => onSelect(item)}
                  sx={{
                    px: 1.5,
                    py: 1,
                    borderBottom: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    opacity: dimmed ? 0.55 : 1,
                    '&.Mui-selected': {
                      bgcolor: 'var(--accent)',
                      '&:hover': { bgcolor: 'var(--accent)' },
                    },
                    '&:hover': { bgcolor: 'var(--bg-primary)' },
                  }}
                >
                  {/* Item image / default icon */}
                  <Box
                    sx={{
                      width: 28,
                      height: 28,
                      flexShrink: 0,
                      borderRadius: 1,
                      overflow: 'hidden',
                      mt: '2px',
                    }}
                  >
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        width={28}
                        height={28}
                        style={{ objectFit: 'cover', display: 'block' }}
                      />
                    ) : (
                      <LAMarketplaceIcon
                        size={28}
                        color={isSelected ? '#fff' : 'var(--accent)'}
                        seed={item.laui}
                      />
                    )}
                  </Box>

                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    {/* Name row */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography
                        sx={{
                          color: isSelected ? '#fff' : 'var(--text-primary)',
                          fontWeight: 600,
                          fontSize: '13px',
                          lineHeight: 1.3,
                          flex: 1,
                          minWidth: 0,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {item.name}
                      </Typography>
                      {isOfficial && (
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            bgcolor: 'success.main',
                            flexShrink: 0,
                          }}
                          title="Official LeastAction"
                        />
                      )}
                      {isVerified && (
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            bgcolor: '#1976d2',
                            flexShrink: 0,
                          }}
                          title="Verified"
                        />
                      )}
                      {dimmed && (
                        <Tooltip title={warningTip} placement="right">
                          <WarningAmberIcon
                            sx={{
                              fontSize: 13,
                              color: incompatible ? 'error.main' : 'warning.main',
                              flexShrink: 0,
                            }}
                          />
                        </Tooltip>
                      )}
                    </Box>

                    {/* Meta chips row */}
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.5,
                        mt: 0.25,
                        flexWrap: 'wrap',
                      }}
                    >
                      {item.item_type && (
                        <Chip
                          label={item.item_type}
                          size="small"
                          sx={{
                            fontSize: '10px',
                            height: '16px',
                            bgcolor: isSelected ? 'rgba(255,255,255,0.25)' : 'var(--bg-primary)',
                            color: isSelected ? '#fff' : 'var(--text-secondary)',
                          }}
                        />
                      )}
                      {item.category && (
                        <Chip
                          label={item.category}
                          size="small"
                          sx={{
                            fontSize: '10px',
                            height: '16px',
                            bgcolor: isSelected ? 'rgba(255,255,255,0.2)' : 'var(--bg-primary)',
                            color: isSelected ? '#fff' : 'var(--text-secondary)',
                          }}
                        />
                      )}
                      {/* Publisher chip */}
                      <Chip
                        label={item.publisher ?? 'Unknown'}
                        size="small"
                        sx={{
                          fontSize: '10px',
                          height: '16px',
                          bgcolor: isOfficial
                            ? isSelected
                              ? 'rgba(255,255,255,0.25)'
                              : 'success.dark'
                            : isSelected
                              ? 'rgba(255,255,255,0.15)'
                              : 'var(--bg-primary)',
                          color: isOfficial
                            ? '#fff'
                            : isSelected
                              ? 'rgba(255,255,255,0.85)'
                              : 'var(--text-secondary)',
                          fontStyle: item.publisher ? 'normal' : 'italic',
                        }}
                      />
                      {item.description && !item.category && (
                        <Typography
                          sx={{
                            color: isSelected ? 'rgba(255,255,255,0.75)' : 'var(--text-secondary)',
                            fontSize: '11px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            maxWidth: '140px',
                          }}
                        >
                          {item.description}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  {/* Import button — right side, only when compatible & not deprecated */}
                  {importBtn}
                </ListItemButton>
              );
            })}
          </List>
        )}
        {isLoadingMore && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 1 }}>
            <CircularProgress size={16} sx={{ color: 'var(--accent)' }} />
          </Box>
        )}
      </Box>

      {/* Footer: publisher of selected item + item count + import */}
      {!isLoading &&
        results.length > 0 &&
        (() => {
          const sel = results.find((r) => r.laui === selectedLaui);
          if (!sel)
            return (
              <Box
                sx={{
                  px: 2,
                  py: 1,
                  borderTop: 1,
                  borderColor: 'var(--border-color)',
                }}
              >
                <Typography sx={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                  {results.length} item{results.length !== 1 ? 's' : ''}
                </Typography>
              </Box>
            );

          const selTypeSupported = schemaExists(sel.item_type);
          const selIncompat = !isCoreCompatible(sel.version_compatibility, getCoreVersion());
          const selDeprecated = !!sel.version_details?.deprecated;
          const selShowImport = selTypeSupported && !selIncompat && !selDeprecated;
          const selIsOfficial = sel.publisher === 'LeastAction';

          const footerImportBtn = selShowImport ? (
            <Tooltip title={`Import "${sel.name}"`} placement="top">
              <IconButton
                size="small"
                onClick={() => setImportModalState({ isOpen: true, itemData: sel })}
                sx={{ color: 'var(--text-primary)', p: 0.5 }}
              >
                <ImportIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          ) : null;

          return (
            <Box
              sx={{
                px: 1.5,
                py: 0.75,
                borderTop: 1,
                borderColor: 'var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              {/* Publisher chip */}
              <Chip
                label={sel.publisher ?? 'Unknown'}
                size="small"
                sx={{
                  fontSize: '10px',
                  height: '18px',
                  bgcolor: selIsOfficial ? 'success.dark' : 'var(--bg-primary)',
                  color: selIsOfficial ? '#fff' : 'var(--text-secondary)',
                  fontStyle: sel.publisher ? 'normal' : 'italic',
                  flexShrink: 0,
                }}
              />
              {/* Item count */}
              <Typography sx={{ color: 'var(--text-secondary)', fontSize: '11px', flex: 1 }}>
                {results.length} item{results.length !== 1 ? 's' : ''}
              </Typography>
              {/* Import button for selected item — hidden when incompatible or deprecated */}
              {footerImportBtn}
            </Box>
          );
        })()}
    </Box>
  );
}
