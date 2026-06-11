/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useContext, useEffect, useMemo, useRef, useState } from 'react';

import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import {
  Autocomplete,
  Box,
  CircularProgress,
  IconButton,
  type SxProps,
  TextField,
  type Theme,
} from '@mui/material';

import { GlobalContext } from '@/contexts/GlobalContext';
import {
  type SearchCatalogFilters,
  getCatalogItemById,
  searchCatalogItems,
} from '@/services/catalog.service';

interface QuickSearchProps {
  /** Pre-populate / control the search input text */
  substringInput?: string;
  /** Current selected LAUI value – resolves to name and pre-fills the input on mount */
  value?: string | null;
  /** Filter results to children of this parent LAUI */
  parentLaui?: string;
  /** Additional catalog filters (e.g. item_type) */
  filters?: Omit<SearchCatalogFilters, 'parent_laui'>;
  /** Called with the full raw API object (or URL string when returnUrl=true) when the user selects an item */
  onSelect: (item: unknown) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  /** Field from the raw item to show alongside the name for disambiguation (e.g. "partition") */
  disambigField?: string;
  /** When true, options render as clickable href links and onSelect receives the URL string */
  returnUrl?: boolean;
  /** Extra sx passed to the inner TextField (merged with defaults) */
  inputSx?: SxProps<Theme>;
  /** When true, disables automatic project-scoping from GlobalContext */
  ignoreProjectScope?: boolean;
}

interface SearchOption {
  label: string;
  name: string;
  laui: string;
  raw: unknown;
  url?: string;
  path?: string;
}

function buildUrl(actual: Record<string, unknown>, laui: string): string {
  const itemType = (actual.item_type as string) ?? '';
  const name = (actual.name as string) ?? '';
  const params = new URLSearchParams({ itemtype: itemType, itemname: name, laui });
  return `${window.location.origin}/path?${params.toString()}`;
}

function toOptions(items: unknown[], disambigField?: string, returnUrl?: boolean): SearchOption[] {
  return items.map((item) => {
    const anyItem = item as Record<string, unknown>;
    const actual = (anyItem.item as Record<string, unknown>) ?? anyItem;
    const laui = (actual._laui as string) ?? (actual.laui as string) ?? (actual.id as string) ?? '';
    const name = (actual.name as string) ?? laui ?? 'Unnamed';
    const disambigValue = disambigField ? ((actual[disambigField] as string) ?? '') : '';
    const disambig = disambigValue && disambigValue !== 'ALL' ? disambigValue : laui;
    const url = returnUrl ? buildUrl(actual, laui) : undefined;
    const parentLaui = (actual.parent_laui as string) ?? '';
    const path = parentLaui ? parentLaui : undefined;
    return { label: `${name} (${disambig})`, name, laui, raw: actual, url, path };
  });
}

const DEBOUNCE_MS = 300;

const EASTER_EGG_LAUI = '__physics_easter_egg__';
const EASTER_EGGS: [string, string][] = [
  ['schrodinger', "⚛ This item exists and doesn't exist simultaneously"],
  ['schrödinger', "⚛ This item exists and doesn't exist simultaneously"],
  ['heisenberg', "⚛ We know where it is, but not where it's going"],
  ['planck', '⚛ Quantized. Minimum resolution: 6.626 × 10⁻³⁴ J·s'],
  ['einstein', '⚛ Results adjusted for time dilation'],
  ['feynman', '⚛ All paths considered — this one had the least action'],
  ['entropy', '⚛ Searching for order in the chaos…'],
  ['42', '⚛ The answer to life, the universe, and everything'],
];

export function QuickSearch({
  substringInput = '',
  value,
  parentLaui,
  filters,
  onSelect,
  label,
  placeholder = 'Search…',
  disabled = false,
  disambigField,
  returnUrl = false,
  inputSx,
  ignoreProjectScope = false,
}: QuickSearchProps) {
  const globalCtx = useContext(GlobalContext);
  const contextProjectLaui = ignoreProjectScope ? null : (globalCtx?.currentProjectLaui ?? null);
  const [inputValue, setInputValue] = useState(substringInput);
  const [options, setOptions] = useState<SearchOption[]>([]);
  const [loading, setLoading] = useState(false);

  const easterEggLine = useMemo(() => {
    const lower = inputValue.trim().toLowerCase();
    return EASTER_EGGS.find(([key]) => lower.includes(key))?.[1] ?? null;
  }, [inputValue]);

  const displayOptions = useMemo<SearchOption[]>(() => {
    if (!easterEggLine) return options;
    return [{ label: easterEggLine, name: '', laui: EASTER_EGG_LAUI, raw: {} }, ...options];
  }, [options, easterEggLine]);

  // Track whether we've already resolved the value prop to a name
  const prefillDoneRef = useRef(false);

  // Keep latest filters in a ref so the debounced callback always sees current values
  const filtersRef = useRef({
    parentLaui,
    filters,
    disambigField,
    returnUrl,
    contextProjectLaui,
  });
  filtersRef.current = { parentLaui, filters, disambigField, returnUrl, contextProjectLaui };

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cache resolved parent names to avoid redundant fetches
  const parentNameCacheRef = useRef<Map<string, string>>(new Map());

  // Cache laui → resolved display label so re-selection shows name instantly
  const resolvedLabelCacheRef = useRef<Map<string, string>>(new Map());
  // Suppress the next debounced search when inputValue is set programmatically
  const suppressSearchRef = useRef(false);

  // Sync external substringInput
  useEffect(() => {
    suppressSearchRef.current = true;
    setInputValue(substringInput);
  }, [substringInput]);

  // Reset prefill tracking when value changes so a new value gets resolved
  useEffect(() => {
    if (!value) {
      prefillDoneRef.current = false;
      suppressSearchRef.current = true;
      setInputValue('');
      return;
    }
    // Use cached label immediately — avoids flash of raw LAUI on re-selection
    const cached = resolvedLabelCacheRef.current.get(value);
    if (cached) {
      suppressSearchRef.current = true;
      setInputValue(cached);
      prefillDoneRef.current = true;
      return;
    }
    prefillDoneRef.current = false;
    suppressSearchRef.current = true;
    setInputValue(value); // show raw LAUI while resolving
    if (disabled) return;
    // Resolve directly by ID — reliable regardless of search pagination
    getCatalogItemById(value)
      .then((item) => {
        if (prefillDoneRef.current) return;
        const actual =
          ((item as Record<string, unknown>).item as Record<string, unknown>) ??
          (item as Record<string, unknown>);
        const name = (actual.name as string) ?? value;
        const laui = (actual._laui as string) ?? (actual.laui as string) ?? value;
        const df = filtersRef.current.disambigField;
        const disambigValue = df ? ((actual[df] as string) ?? '') : '';
        const disambig = disambigValue && disambigValue !== 'ALL' ? disambigValue : laui;
        const label = `${name} (${disambig})`;
        resolvedLabelCacheRef.current.set(value, label);
        prefillDoneRef.current = true;
        suppressSearchRef.current = true;
        setInputValue(label);
      })
      .catch(() => {
        /* keep showing raw LAUI */
      });
  }, [value, disabled]);

  const fetchOptions = (query: string) => {
    const {
      parentLaui: pl,
      filters: f,
      disambigField: df,
      returnUrl: ru,
      contextProjectLaui: cpl,
    } = filtersRef.current;
    const combinedFilters: SearchCatalogFilters = {
      ...(cpl ? { project_laui: cpl } : {}),
      ...f,
      ...(pl ? { parent_laui: pl } : {}),
      ...(query ? { name: query } : {}),
    };

    setLoading(true);
    searchCatalogItems(undefined, false, {
      filters: combinedFilters,
      perPage: 10,
      projection: ['name', 'action_variables', 'parent_laui'],
    })
      .then((response) => {
        const items = (response?.items ?? response ?? []) as unknown[];
        const nextOptions = Array.isArray(items) ? toOptions(items, df, ru) : [];

        // Show options immediately so the dropdown isn't empty while parent names load
        setOptions(nextOptions);
        setLoading(false);

        // If we haven't pre-filled the name yet and value is set, do it now from fetched options
        if (value && !prefillDoneRef.current) {
          const found = nextOptions.find((o) => o.laui === value);
          if (found) {
            resolvedLabelCacheRef.current.set(value, found.label);
            prefillDoneRef.current = true;
            suppressSearchRef.current = true;
            setInputValue(found.label);
          }
        }

        // Resolve parent names in background and update path labels
        const cache = parentNameCacheRef.current;
        const unresolvedLauis = [
          ...new Set(
            nextOptions.map((o) => o.path).filter((p): p is string => !!p && !cache.has(p)),
          ),
        ];
        if (unresolvedLauis.length > 0) {
          void Promise.all(
            unresolvedLauis.map(async (laui) => {
              try {
                const item = await getCatalogItemById(laui);
                const actualItem =
                  ((item as Record<string, unknown>).item as Record<string, unknown>) ??
                  (item as Record<string, unknown>);
                cache.set(laui, (actualItem.name as string) ?? laui);
              } catch {
                cache.set(laui, laui);
              }
            }),
          ).then(() => {
            setOptions((prev) =>
              prev.map((o) =>
                o.path && cache.has(o.path) ? { ...o, path: cache.get(o.path) } : o,
              ),
            );
          });
        }
      })
      .catch((err) => {
        console.error('QuickSearch fetch error:', err);
        setOptions([]);
        setLoading(false);
      });
  };

  // Fire a server-side search on every input change (debounced)
  // Skipped when inputValue was set programmatically (value resolution / substringInput sync)
  useEffect(() => {
    if (suppressSearchRef.current) {
      suppressSearchRef.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const query = inputValue.trim();

    debounceRef.current = setTimeout(() => fetchOptions(query), DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [inputValue]);

  return (
    <Autocomplete<SearchOption, false, false, false>
      fullWidth
      size="small"
      disabled={disabled}
      options={displayOptions}
      loading={loading}
      value={null}
      inputValue={inputValue}
      onOpen={() => {
        if (options.length === 0) fetchOptions(inputValue.trim());
      }}
      onInputChange={(_e, v, reason) => {
        if (reason === 'input' || reason === 'clear') setInputValue(v);
      }}
      onChange={(_e, newValue) => {
        if (newValue && newValue.laui !== EASTER_EGG_LAUI)
          onSelect(returnUrl ? (newValue.url ?? newValue.raw) : newValue.raw);
      }}
      getOptionLabel={(o) => (returnUrl ? (o.url ?? o.label) : o.label)}
      isOptionEqualToValue={(a, b) => a.laui === b.laui}
      filterOptions={(x) => x} // server already filtered
      noOptionsText={inputValue.trim() ? 'No results' : 'Type to search…'}
      renderOption={(props, option) => {
        if (option.laui === EASTER_EGG_LAUI) {
          const { key, ...rest } = props as React.HTMLAttributes<HTMLElement> & {
            key?: React.Key;
          };
          return (
            <li
              key={key}
              {...rest}
              style={{
                padding: '6px 12px',
                cursor: 'default',
                pointerEvents: 'none',
              }}
            >
              <span
                style={{
                  fontSize: '11px',
                  fontStyle: 'italic',
                  color: 'var(--text-secondary)',
                  opacity: 0.7,
                }}
              >
                {option.label}
              </span>
            </li>
          );
        }
        return returnUrl ? (
          <li {...props} key={option.laui} style={{ padding: 0 }}>
            <a
              href={option.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                e.stopPropagation();
                window.open(option.url, '_blank', 'noopener,noreferrer');
                e.preventDefault();
              }}
              style={{
                display: 'block',
                width: '100%',
                padding: '6px 16px',
                color: 'var(--text-link, #4a9eff)',
                textDecoration: 'none',
                fontSize: '12px',
              }}
            >
              {option.url
                ? (option.url.split('?')[1]?.replace(/&/g, '  ') ?? option.label)
                : option.label}
            </a>
          </li>
        ) : (
          <li
            {...props}
            key={option.laui}
            style={{
              display: 'flex',
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '4px 8px 4px 12px',
            }}
          >
            <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
              <span style={{ fontSize: '12px', color: 'var(--text-primary)' }}>{option.label}</span>
              {option.path && (
                <span
                  style={{
                    fontSize: '10px',
                    color: 'var(--text-secondary)',
                    marginTop: '1px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {option.path}/{option.name}
                </span>
              )}
            </Box>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                const url = buildUrl(option.raw as Record<string, unknown>, option.laui);
                window.open(url, '_blank', 'noopener,noreferrer');
              }}
              sx={{
                color: 'var(--text-secondary)',
                p: 0.25,
                ml: 0.5,
                flexShrink: 0,
                opacity: 0.6,
                '&:hover': { opacity: 1, color: 'var(--text-primary)' },
              }}
            >
              <OpenInNewIcon sx={{ fontSize: 13 }} />
            </IconButton>
          </li>
        );
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder}
          InputLabelProps={{
            ...params.InputLabelProps,
            // Force the label to shrink when the input holds a value (e.g. a
            // programmatically prefilled selection). Without this MUI keeps the
            // label un-shrunk and it overlaps the prefilled text.
            shrink: inputValue.trim().length > 0,
          }}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading && <CircularProgress color="inherit" size={20} />}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              minHeight: '32px',
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(var(--color-border), 0.3)',
              },
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(var(--color-border), 0.6)',
              },
              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                borderColor: 'var(--accent)',
              },
            },
            '& .MuiInputBase-input': {
              padding: '6px 12px',
              fontSize: '12px',
              color: 'var(--text-primary)',
              // Keep prefilled text readable when the field is disabled — MUI
              // otherwise dims it to an unreadable grey on the dark theme.
              '&.Mui-disabled': {
                color: 'var(--text-primary)',
                WebkitTextFillColor: 'var(--text-primary)',
                opacity: 1,
              },
            },
            '& .Mui-disabled .MuiOutlinedInput-notchedOutline': {
              borderColor: 'rgba(var(--color-border), 0.3)',
            },
            '& .MuiInputLabel-root': {
              color: 'var(--text-secondary)',
              fontSize: '12px',
              '&.Mui-focused': {
                color: 'var(--accent)',
              },
              '&.Mui-disabled': {
                color: 'var(--text-secondary)',
              },
            },
            ...inputSx,
          }}
        />
      )}
      slotProps={{
        paper: {
          sx: {
            bgcolor: 'var(--bg-secondary)',
            border: '1px solid rgba(var(--color-border), 0.3)',
            '& .MuiAutocomplete-option': {
              color: 'var(--text-primary)',
              fontSize: '12px',
              '&:hover': { bgcolor: 'rgba(var(--color-text-base), 0.06)' },
              '&.Mui-focused': { bgcolor: 'rgba(var(--color-text-base), 0.06)' },
            },
            '& .MuiAutocomplete-noOptions': {
              color: 'var(--text-secondary)',
              fontSize: '12px',
            },
          },
        },
      }}
      sx={{
        '& .MuiAutocomplete-popupIndicator': { color: 'var(--text-secondary)' },
        '& .MuiAutocomplete-clearIndicator': { color: 'var(--text-secondary)' },
      }}
    />
  );
}
