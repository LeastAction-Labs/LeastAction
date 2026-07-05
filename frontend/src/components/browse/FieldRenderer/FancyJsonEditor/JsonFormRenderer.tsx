/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useRef, useState } from 'react';

import { flushSync } from 'react-dom';

import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Chip,
  IconButton,
  MenuItem,
  Select,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material';

import { QuickSearch } from '@/components/ui/QuickSearch';

import { getDataType, getItemTypeFromKey, isLauiKey, isLockedValue } from './fieldDetection';

// ── Type badge metadata ────────────────────────────────────────────────
// Semantic type colors — fixed hues (like syntax highlighting), work on both dark/light
// because bg uses low-opacity rgba (blends with any theme bg) and fg is the full-sat color
const TYPE_META: Record<
  string,
  { label: string; bg: string; fg: string; border: string; line: string }
> = {
  object: {
    label: 'OBJECT',
    bg: 'rgba(0, 188, 212, 0.14)',
    fg: '#00bcd4',
    border: 'rgba(0, 188, 212, 0.35)',
    line: '#00bcd4',
  },
  array: {
    label: 'ARRAY',
    bg: 'rgba(233, 30, 99, 0.14)',
    fg: '#e91e63',
    border: 'rgba(233, 30, 99, 0.35)',
    line: '#e91e63',
  },
  string: {
    label: 'STRING',
    bg: 'rgba(128,128,128, 0.10)',
    fg: 'var(--text-dim)',
    border: 'rgba(128,128,128,0.25)',
    line: 'rgba(128,128,128,0.4)',
  },
  number: {
    label: 'NUMBER',
    bg: 'rgba(33, 150, 243, 0.14)',
    fg: '#2196f3',
    border: 'rgba(33, 150, 243, 0.35)',
    line: '#2196f3',
  },
  boolean: {
    label: 'BOOLEAN',
    bg: 'rgba(156, 39, 176, 0.14)',
    fg: '#9c27b0',
    border: 'rgba(156, 39, 176, 0.35)',
    line: '#9c27b0',
  },
  null: {
    label: 'NULL',
    bg: 'rgba(128,128,128, 0.10)',
    fg: 'var(--text-dim)',
    border: 'rgba(128,128,128,0.25)',
    line: 'rgba(128,128,128,0.4)',
  },
};

function TypeBadge({ type, count }: { type: string; count?: number }) {
  const meta = TYPE_META[type] ?? TYPE_META.string;
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        px: 0.75,
        py: 0.25,
        bgcolor: meta.bg,
        color: meta.fg,
        border: `1px solid ${meta.border}`,
        borderRadius: '3px',
        fontSize: '9px',
        fontWeight: 800,
        letterSpacing: '0.1em',
        whiteSpace: 'nowrap',
        flexShrink: 0,
        lineHeight: 1.6,
      }}
    >
      {meta.label}
      {count !== undefined ? ` [${count}]` : ''}
    </Box>
  );
}

// ── Shared style constants ──────────────────────────────────────────────
type ValueType = 'object' | 'array' | 'string' | 'number' | 'boolean';

const DEFAULT_FOR_TYPE: Record<ValueType, unknown> = {
  object: {},
  array: [],
  string: '',
  number: 0,
  boolean: false,
};

const TEXT_FIELD_SX = {
  '& .MuiOutlinedInput-root': {
    bgcolor: 'var(--bg-primary)',
    fontSize: '13px',
    color: 'var(--text-primary)',
    '& fieldset': { borderColor: 'var(--border)' },
    '&:hover fieldset': { borderColor: 'var(--text-secondary)' },
    '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
    '&.Mui-disabled': { bgcolor: 'var(--bg-secondary)', opacity: 1 },
    '&.Mui-disabled input': { WebkitTextFillColor: 'var(--text-primary)', opacity: 1 },
  },
  '& .MuiInputLabel-root': {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    '&.Mui-focused': { color: 'var(--accent)' },
    '&.Mui-disabled': { color: 'var(--text-secondary)' },
    '&.MuiInputLabel-shrink': { color: 'var(--text-primary)', fontSize: '12px' },
    '&.MuiInputLabel-shrink.Mui-focused': { color: 'var(--accent)' },
  },
};

const SELECT_SX = {
  fontSize: '12px',
  color: 'var(--text-primary)',
  bgcolor: 'var(--bg-primary)',
  '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border)' },
  '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--text-secondary)' },
  '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--accent)' },
  '& .MuiSelect-icon': { color: 'var(--text-secondary)' },
};

// ── CollapsibleSection (replaces MUI Accordion) ─────────────────────────
function CollapsibleSection({
  label,
  type,
  count,
  defaultExpanded = true,
  rightSlot,
  children,
}: {
  label: string;
  type: 'object' | 'array';
  count?: number;
  defaultExpanded?: boolean;
  rightSlot?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const meta = TYPE_META[type];

  return (
    <Box>
      <Box
        onClick={() => setExpanded(!expanded)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.75,
          cursor: 'pointer',
          py: 0.5,
          px: 0.25,
          borderRadius: 1,
          userSelect: 'none',
          '&:hover': { bgcolor: 'var(--bg-tertiary)' },
        }}
      >
        <ExpandMoreIcon
          sx={{
            fontSize: 18,
            color: 'var(--text-secondary)',
            transform: expanded ? 'rotate(0deg)' : 'rotate(-90deg)',
            transition: 'transform 0.18s ease',
            flexShrink: 0,
          }}
        />
        <Typography
          sx={{
            fontSize: '14px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            letterSpacing: '0.01em',
          }}
        >
          {label}
        </Typography>
        <TypeBadge type={type} count={type === 'array' ? count : undefined} />
        {rightSlot && (
          <Box sx={{ ml: 'auto' }} onClick={(e) => e.stopPropagation()}>
            {rightSlot}
          </Box>
        )}
      </Box>

      {expanded && (
        <Box
          sx={{
            ml: 1.25,
            pl: 1.75,
            borderLeft: `1px solid ${meta.line}22`,
            display: 'flex',
            flexDirection: 'column',
            gap: 0.75,
            pt: 0.5,
            pb: 0.25,
          }}
        >
          {children}
        </Box>
      )}
    </Box>
  );
}

// ── PrimitiveFieldRow ───────────────────────────────────────────────────
// Clean row for string / number / boolean primitives
function PrimitiveReadOnlyRow({
  fieldKey,
  value,
  type,
}: {
  fieldKey: string;
  value: unknown;
  type: string;
}) {
  const meta = TYPE_META[type] ?? TYPE_META.string;
  const stringifyValue = (v: unknown): string => {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v as string | number | boolean);
  };
  const display = type === 'boolean' ? stringifyValue(value).toUpperCase() : stringifyValue(value);

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 1.5,
        py: 1.1,
        bgcolor: 'var(--bg-secondary)',
        borderRadius: '0 4px 4px 0',
        borderLeft: `3px solid ${meta.line}`,
        minHeight: 40,
      }}
    >
      <Typography
        sx={{
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
          minWidth: 80,
          flexShrink: 0,
        }}
      >
        {fieldKey}
      </Typography>
      <Box sx={{ flex: 1 }} />
      <Typography
        sx={{
          fontSize: '13px',
          color: 'var(--text-primary)',
          fontWeight: 500,
          textAlign: 'right',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: '55%',
        }}
      >
        {display}
      </Typography>
      <TypeBadge type={type} />
    </Box>
  );
}

// ── AddKeyRow ───────────────────────────────────────────────────────────
function AddKeyRow({ onAdd }: { onAdd: (key: string, val: unknown) => void }) {
  const [key, setKey] = useState('');
  const [valueType, setValueType] = useState<ValueType | ''>('');
  const [strVal, setStrVal] = useState('');
  const [numVal, setNumVal] = useState('0');
  const [boolVal, setBoolVal] = useState(true);
  const [arrItems, setArrItems] = useState<string[]>([]);
  const [arrInput, setArrInput] = useState('');

  const isLaui = isLauiKey(key);
  const itemType = isLaui ? getItemTypeFromKey(key) : '';
  const effectiveType: ValueType | '' = isLaui ? 'string' : valueType;
  const canCommit = key.trim() !== '' && (isLaui || effectiveType !== '');

  const pendingRef = useRef(false);

  const commit = (overrideVal?: unknown) => {
    if (!canCommit || pendingRef.current) return;
    pendingRef.current = true;
    let val: unknown;
    if (overrideVal !== undefined) {
      val = overrideVal;
    } else if (effectiveType === 'string') {
      val = strVal;
    } else if (effectiveType === 'number') {
      val = parseFloat(numVal) || 0;
    } else if (effectiveType === 'boolean') {
      val = boolVal;
    } else if (effectiveType === 'array') {
      const finalItems = arrInput.trim() ? [...arrItems, arrInput.trim()] : arrItems;
      val = finalItems;
    } else {
      val = DEFAULT_FOR_TYPE[effectiveType as ValueType];
    }
    onAdd(key.trim(), val);
    setKey('');
    setStrVal('');
    setNumVal('0');
    setBoolVal(true);
    setValueType('');
    setArrItems([]);
    setArrInput('');
    requestAnimationFrame(() => {
      pendingRef.current = false;
    });
  };

  const FIELD_WRAPPER_SX = { flex: '1 1 0', minWidth: 0, display: 'flex' };

  const pushArrItem = () => {
    if (!arrInput.trim()) return;
    setArrItems((prev) => [...prev, arrInput.trim()]);
    setArrInput('');
  };

  const renderValueInput = () => {
    if (!effectiveType) return <Box sx={FIELD_WRAPPER_SX} />;
    if (isLaui) {
      return (
        <Box sx={FIELD_WRAPPER_SX}>
          <QuickSearch
            label={`Search ${itemType}`}
            value={strVal}
            filters={{ item_type: itemType }}
            disambigField={itemType === 'task' ? 'partition' : undefined}
            onSelect={(rawItem) => {
              const raw = rawItem as Record<string, unknown>;
              const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
              setStrVal(laui);
              commit(laui);
            }}
            placeholder={`Search ${itemType}…`}
          />
        </Box>
      );
    }
    if (effectiveType === 'string') {
      return (
        <Box sx={FIELD_WRAPPER_SX}>
          <TextField
            size="small"
            fullWidth
            label="Value"
            value={strVal}
            onChange={(e) => setStrVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && commit()}
            onBlur={() => canCommit && flushSync(() => commit())}
            sx={TEXT_FIELD_SX}
          />
        </Box>
      );
    }
    if (effectiveType === 'number') {
      return (
        <Box sx={FIELD_WRAPPER_SX}>
          <TextField
            size="small"
            fullWidth
            type="number"
            label="Value"
            value={numVal}
            onChange={(e) => setNumVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && commit()}
            onBlur={() => canCommit && flushSync(() => commit())}
            sx={TEXT_FIELD_SX}
          />
        </Box>
      );
    }
    if (effectiveType === 'boolean') {
      return (
        <Box sx={FIELD_WRAPPER_SX}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={boolVal}
            onChange={(_, v) => {
              if (v !== null) setBoolVal(v);
            }}
            sx={{
              '& .MuiToggleButton-root': {
                color: 'var(--text-secondary)',
                borderColor: 'var(--border)',
                fontSize: '12px',
                px: 2,
                '&.Mui-selected': {
                  bgcolor: 'var(--accent)',
                  color: '#fff',
                  '&:hover': { bgcolor: 'var(--accent)' },
                },
              },
            }}
          >
            <ToggleButton value={true}>True</ToggleButton>
            <ToggleButton value={false}>False</ToggleButton>
          </ToggleButtonGroup>
        </Box>
      );
    }
    if (effectiveType === 'array') {
      return (
        <Box sx={FIELD_WRAPPER_SX}>
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: 0.5,
              minHeight: 40,
              px: 1.5,
              py: 0.5,
              border: '1px solid var(--border)',
              borderRadius: 1,
              bgcolor: 'var(--bg-primary)',
              cursor: 'text',
              '&:focus-within': { borderColor: 'var(--accent)' },
            }}
            onClick={() => document.getElementById('arr-item-input')?.focus()}
          >
            {arrItems.map((item, i) => (
              <Chip
                key={i}
                label={item}
                size="small"
                onDelete={() => setArrItems((prev) => prev.filter((_, idx) => idx !== i))}
                sx={{
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  fontSize: '11px',
                  height: 22,
                  '& .MuiChip-deleteIcon': {
                    color: 'var(--text-secondary)',
                    fontSize: 14,
                  },
                }}
              />
            ))}
            <input
              id="arr-item-input"
              value={arrInput}
              onChange={(e) => setArrInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ',') {
                  e.preventDefault();
                  pushArrItem();
                }
              }}
              placeholder={arrItems.length === 0 ? 'Type item, press Enter…' : ''}
              style={{
                border: 'none',
                outline: 'none',
                background: 'transparent',
                color: 'var(--text-primary)',
                fontSize: '13px',
                flex: '1 1 60px',
                minWidth: 60,
                padding: '2px 0',
              }}
            />
          </Box>
        </Box>
      );
    }
    // object
    return (
      <Box
        sx={{
          ...FIELD_WRAPPER_SX,
          alignItems: 'center',
          px: 1.5,
          border: '1px solid var(--border)',
          borderRadius: 1,
          color: 'var(--text-secondary)',
          fontSize: '12px',
          height: 40,
        }}
      >
        Empty object will be created
      </Box>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        gap: 1,
        alignItems: 'center',
        mt: 0.5,
        p: 1.5,
        border: '1px dashed var(--border)',
        borderRadius: 1,
        bgcolor: 'var(--bg-secondary)',
      }}
    >
      {!isLaui && (
        <Select
          size="small"
          value={valueType}
          displayEmpty
          onChange={(e) => setValueType(e.target.value as ValueType)}
          sx={{ width: 110, flexShrink: 0, ...SELECT_SX }}
          renderValue={(v) =>
            v ? String(v) : <span style={{ color: 'var(--text-secondary)' }}>Type</span>
          }
          MenuProps={{
            PaperProps: {
              sx: {
                bgcolor: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                fontSize: '12px',
              },
            },
          }}
        >
          {(['object', 'array', 'string', 'number', 'boolean'] as ValueType[]).map((t) => (
            <MenuItem key={t} value={t} sx={{ fontSize: '12px' }}>
              {t}
            </MenuItem>
          ))}
        </Select>
      )}
      <Box sx={{ flex: '1 1 0', minWidth: 0, display: 'flex' }}>
        <TextField
          size="small"
          fullWidth
          label="New key"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          onKeyDown={(e) =>
            e.key === 'Enter' &&
            (effectiveType === 'string' || effectiveType === 'number') &&
            !isLaui &&
            commit()
          }
          sx={TEXT_FIELD_SX}
        />
      </Box>
      {renderValueInput()}
      <Tooltip title={canCommit ? 'Add key' : 'Select a type and enter a key first'}>
        <span>
          <IconButton
            size="small"
            onClick={() => commit()}
            disabled={!canCommit}
            sx={{
              flexShrink: 0,
              color: canCommit ? 'var(--accent)' : 'var(--text-secondary)',
              '&:hover': { bgcolor: 'var(--bg-tertiary)' },
            }}
          >
            <AddIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    </Box>
  );
}

// ── ArrayItemRow ────────────────────────────────────────────────────────
function ArrayItemRow({
  idx,
  item,
  readOnly,
  onChangeItem,
  onRemove,
}: {
  idx: number;
  item: unknown;
  readOnly: boolean;
  onChangeItem: (val: unknown) => void;
  onRemove: () => void;
}) {
  const detectedRaw = getDataType(item);
  const detectedType: ValueType = (detectedRaw === 'null' ? 'string' : detectedRaw) as ValueType;
  const [selectedType, setSelectedType] = useState<ValueType>(detectedType);

  const handleTypeChange = (newType: ValueType) => {
    setSelectedType(newType);
    onChangeItem(DEFAULT_FOR_TYPE[newType]);
  };

  // For object items: show an INDEX card
  if (selectedType === 'object') {
    return (
      <Box
        sx={{
          border: '1px solid var(--border)',
          borderRadius: 1.5,
          overflow: 'hidden',
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        {/* INDEX card header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            px: 1.5,
            py: 0.875,
            borderBottom: '1px solid var(--border)',
            bgcolor: 'var(--bg-tertiary)',
          }}
        >
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: TYPE_META.array.fg,
              flexShrink: 0,
            }}
          />
          <Typography
            sx={{
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
            }}
          >
            Index [{idx}]
          </Typography>
          {!readOnly && (
            <Box sx={{ ml: 'auto', display: 'flex', gap: 0.5, alignItems: 'center' }}>
              <Select
                size="small"
                value={selectedType}
                onChange={(e) => handleTypeChange(e.target.value as ValueType)}
                sx={{ width: 90, ...SELECT_SX, fontSize: '11px' }}
                MenuProps={{
                  PaperProps: {
                    sx: {
                      bgcolor: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                    },
                  },
                }}
              >
                {(['object', 'array', 'string', 'number', 'boolean'] as ValueType[]).map((t) => (
                  <MenuItem key={t} value={t} sx={{ fontSize: '12px' }}>
                    {t}
                  </MenuItem>
                ))}
              </Select>
              <IconButton size="small" onClick={onRemove} sx={{ color: 'var(--text-secondary)' }}>
                <DeleteIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Box>
          )}
        </Box>
        <Box sx={{ p: 1.5 }}>
          <JsonFormRenderer
            parsedValue={(item as Record<string, unknown>) ?? {}}
            readOnly={readOnly}
            onUiChange={(k, v) => onChangeItem({ ...(item as Record<string, unknown>), [k]: v })}
            onAddKey={(k, v) => onChangeItem({ ...(item as Record<string, unknown>), [k]: v })}
            onRemoveKey={(k) => {
              const next = { ...(item as Record<string, unknown>) };
              delete next[k];
              onChangeItem(next);
            }}
          />
        </Box>
      </Box>
    );
  }

  if (selectedType === 'array') {
    return (
      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-start' }}>
        {!readOnly && (
          <Select
            size="small"
            value={selectedType}
            onChange={(e) => handleTypeChange(e.target.value as ValueType)}
            sx={{ width: 95, flexShrink: 0, alignSelf: 'center', ...SELECT_SX }}
            MenuProps={{
              PaperProps: {
                sx: {
                  bgcolor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                },
              },
            }}
          >
            {(['object', 'array', 'string', 'number', 'boolean'] as ValueType[]).map((t) => (
              <MenuItem key={t} value={t} sx={{ fontSize: '12px' }}>
                {t}
              </MenuItem>
            ))}
          </Select>
        )}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <ArraySection
            arrKey={`Item ${idx + 1}`}
            arr={(item as unknown[]) ?? []}
            readOnly={readOnly}
            onChange={onChangeItem}
          />
        </Box>
        {!readOnly && (
          <IconButton
            size="small"
            onClick={onRemove}
            sx={{ color: 'var(--text-secondary)', mt: 0.5, flexShrink: 0 }}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        )}
      </Box>
    );
  }

  if (selectedType === 'boolean') {
    if (readOnly) {
      return <PrimitiveReadOnlyRow fieldKey={`Item ${idx + 1}`} value={item} type="boolean" />;
    }
    return (
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        {!readOnly && (
          <Select
            size="small"
            value={selectedType}
            onChange={(e) => handleTypeChange(e.target.value as ValueType)}
            sx={{ width: 95, flexShrink: 0, ...SELECT_SX }}
            MenuProps={{
              PaperProps: {
                sx: {
                  bgcolor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                },
              },
            }}
          >
            {(['object', 'array', 'string', 'number', 'boolean'] as ValueType[]).map((t) => (
              <MenuItem key={t} value={t} sx={{ fontSize: '12px' }}>
                {t}
              </MenuItem>
            ))}
          </Select>
        )}
        <Typography
          sx={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-secondary)',
            minWidth: 60,
          }}
        >
          Item {idx + 1}
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={!!item}
          onChange={(_, v) => {
            if (v !== null && !readOnly) onChangeItem(v);
          }}
          disabled={readOnly}
          sx={{
            '& .MuiToggleButton-root': {
              color: 'var(--text-secondary)',
              borderColor: 'var(--border)',
              fontSize: '12px',
              px: 2,
              '&.Mui-selected': {
                bgcolor: 'var(--accent)',
                color: '#fff',
                '&:hover': { bgcolor: 'var(--accent)' },
              },
            },
          }}
        >
          <ToggleButton value={true}>True</ToggleButton>
          <ToggleButton value={false}>False</ToggleButton>
        </ToggleButtonGroup>
        <IconButton size="small" onClick={onRemove} sx={{ color: 'var(--text-secondary)' }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      </Box>
    );
  }

  if (readOnly) {
    return <PrimitiveReadOnlyRow fieldKey={`Item ${idx + 1}`} value={item} type={selectedType} />;
  }

  // Edit mode: number or string
  return (
    <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
      <Select
        size="small"
        value={selectedType}
        onChange={(e) => handleTypeChange(e.target.value as ValueType)}
        sx={{ width: 95, flexShrink: 0, ...SELECT_SX }}
        MenuProps={{
          PaperProps: {
            sx: {
              bgcolor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
            },
          },
        }}
      >
        {(['object', 'array', 'string', 'number', 'boolean'] as ValueType[]).map((t) => (
          <MenuItem key={t} value={t} sx={{ fontSize: '12px' }}>
            {t}
          </MenuItem>
        ))}
      </Select>
      <TextField
        size="small"
        fullWidth
        type={selectedType === 'number' ? 'number' : 'text'}
        label={`Item ${idx + 1}`}
        value={
          selectedType === 'number'
            ? typeof item === 'number'
              ? item
              : 0
            : typeof item === 'string'
              ? item
              : ''
        }
        onChange={(e) =>
          !readOnly &&
          onChangeItem(selectedType === 'number' ? parseFloat(e.target.value) || 0 : e.target.value)
        }
        sx={TEXT_FIELD_SX}
      />
      <IconButton
        size="small"
        onClick={onRemove}
        sx={{ color: 'var(--text-secondary)', flexShrink: 0 }}
      >
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Box>
  );
}

// ── ArraySection ────────────────────────────────────────────────────────
function ArraySection({
  arrKey,
  arr,
  readOnly,
  onChange,
}: {
  arrKey: string;
  arr: unknown[];
  readOnly: boolean;
  onChange: (val: unknown[]) => void;
}) {
  // For read-only string-only arrays, show compact chip row
  const allPrimitives = arr.every((item) => {
    const t = getDataType(item);
    return t === 'string' || t === 'number' || t === 'boolean';
  });

  if (readOnly && allPrimitives && arr.length > 0) {
    return (
      <Box
        sx={{
          px: 1.5,
          py: 1.1,
          bgcolor: 'var(--bg-secondary)',
          borderRadius: '0 4px 4px 0',
          borderLeft: `3px solid ${TYPE_META.array.line}`,
        }}
      >
        <Typography
          sx={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-secondary)',
            mb: 0.75,
          }}
        >
          {arrKey}
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {arr.map((item, i) => (
            <Box
              key={i}
              sx={{
                px: 1,
                py: 0.25,
                bgcolor: TYPE_META.array.bg,
                color: TYPE_META.array.fg,
                border: `1px solid ${TYPE_META.array.border}`,
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.04em',
              }}
            >
              {String(item)}
            </Box>
          ))}
        </Box>
      </Box>
    );
  }

  return (
    <CollapsibleSection label={arrKey} type="array" count={arr.length}>
      {arr.map((item, idx) => (
        <ArrayItemRow
          key={idx}
          idx={idx}
          item={item}
          readOnly={readOnly}
          onChangeItem={(v) => {
            const next = [...arr];
            next[idx] = v;
            onChange(next);
          }}
          onRemove={() => onChange(arr.filter((_, i) => i !== idx))}
        />
      ))}
      {arr.length === 0 && (
        <Typography
          sx={{
            color: 'var(--text-dim)',
            fontSize: '12px',
            fontStyle: 'italic',
            py: 0.5,
          }}
        >
          No items
        </Typography>
      )}
      {!readOnly && (
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={() => onChange([...arr, ''])}
          sx={{
            alignSelf: 'flex-start',
            color: 'var(--accent)',
            fontSize: '12px',
            mt: 0.25,
          }}
        >
          Add item
        </Button>
      )}
    </CollapsibleSection>
  );
}

// ── Schema-driven fixed field row ───────────────────────────────────────
interface PropSchema {
  type: 'string' | 'boolean' | 'array' | 'enum' | 'object';
  items?: string;
  enum_values?: string[];
  description?: string;
}

function SchemaField({
  fieldKey,
  propSchema,
  value,
  readOnly,
  onChange,
}: {
  fieldKey: string;
  propSchema: PropSchema;
  value: unknown;
  readOnly: boolean;
  onChange: (key: string, val: unknown) => void;
}) {
  const label = fieldKey.replace(/_/g, ' ');

  if (propSchema.type === 'boolean') {
    const boolVal = value === true || value === 'true';
    const isFalse = value === false || value === 'false';
    if (readOnly) return <PrimitiveReadOnlyRow fieldKey={fieldKey} value={value} type="boolean" />;
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.5,
          py: 1,
          bgcolor: 'var(--bg-secondary)',
          borderRadius: '0 4px 4px 0',
          borderLeft: `3px solid ${TYPE_META.boolean.line}`,
        }}
      >
        <Typography
          sx={{
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-secondary)',
            minWidth: 100,
            flexShrink: 0,
          }}
        >
          {label}
        </Typography>
        {propSchema.description && (
          <Typography sx={{ fontSize: '11px', color: 'var(--text-dim)', flex: 1 }}>
            {propSchema.description}
          </Typography>
        )}
        <ToggleButtonGroup
          size="small"
          exclusive
          value={boolVal ? true : isFalse ? false : null}
          onChange={(_, v) => {
            if (v !== null) onChange(fieldKey, v);
          }}
          sx={{
            '& .MuiToggleButton-root': {
              color: 'var(--text-secondary)',
              borderColor: 'var(--border)',
              fontSize: '11px',
              px: 1.5,
              '&.Mui-selected': {
                bgcolor: TYPE_META.boolean.fg,
                color: '#fff',
                borderColor: TYPE_META.boolean.fg,
              },
            },
          }}
        >
          <ToggleButton value={true}>True</ToggleButton>
          <ToggleButton value={false}>False</ToggleButton>
        </ToggleButtonGroup>
        <TypeBadge type="boolean" />
      </Box>
    );
  }

  if (propSchema.type === 'enum' && propSchema.enum_values) {
    if (readOnly) return <PrimitiveReadOnlyRow fieldKey={fieldKey} value={value} type="string" />;
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          borderRadius: '0 4px 4px 0',
          borderLeft: `3px solid ${TYPE_META.string.line}`,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Select
            size="small"
            fullWidth
            value={(value as string) || ''}
            displayEmpty
            onChange={(e) => onChange(fieldKey, e.target.value)}
            sx={SELECT_SX}
            renderValue={(v) =>
              v ? (
                String(v)
              ) : (
                <span style={{ color: 'var(--text-dim)' }}>{propSchema.description || label}</span>
              )
            }
            MenuProps={{
              PaperProps: {
                sx: {
                  bgcolor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                },
              },
            }}
          >
            {propSchema.enum_values.map((opt) => (
              <MenuItem key={opt} value={opt} sx={{ fontSize: '12px' }}>
                {opt}
              </MenuItem>
            ))}
          </Select>
        </Box>
        <TypeBadge type="string" />
      </Box>
    );
  }

  if (propSchema.type === 'array') {
    const arr = Array.isArray(value) ? (value as string[]) : [];
    if (readOnly) {
      return <ArraySection arrKey={fieldKey} arr={arr} readOnly onChange={() => {}} />;
    }
    return (
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 0.5,
          minHeight: 40,
          px: 1.5,
          py: 0.5,
          border: '1px solid var(--border)',
          borderRadius: 1,
          bgcolor: 'var(--bg-primary)',
          cursor: 'text',
          '&:focus-within': { borderColor: 'var(--accent)' },
        }}
        onClick={() => document.getElementById(`arr-input-${fieldKey}`)?.focus()}
      >
        {arr.map((item, i) => (
          <Chip
            key={i}
            label={item}
            size="small"
            onDelete={() =>
              onChange(
                fieldKey,
                arr.filter((_, idx) => idx !== i),
              )
            }
            sx={{
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '11px',
              height: 22,
              '& .MuiChip-deleteIcon': {
                color: 'var(--text-secondary)',
                fontSize: 14,
              },
            }}
          />
        ))}
        <SchemaArrayInput
          fieldKey={fieldKey}
          arr={arr}
          onChange={(val) => onChange(fieldKey, val)}
        />
      </Box>
    );
  }

  // string (default)
  if (readOnly) return <PrimitiveReadOnlyRow fieldKey={fieldKey} value={value} type="string" />;
  return (
    <Box sx={{ borderRadius: '0 4px 4px 0', borderLeft: `3px solid ${TYPE_META.string.line}` }}>
      <TextField
        size="small"
        fullWidth
        label={label}
        value={(value as string) ?? ''}
        placeholder={propSchema.description}
        onChange={(e) => onChange(fieldKey, e.target.value)}
        slotProps={{
          input: { endAdornment: <TypeBadge type="string" /> },
          inputLabel: { shrink: true },
        }}
        sx={{
          ...TEXT_FIELD_SX,
          '& .MuiOutlinedInput-root': {
            ...TEXT_FIELD_SX['& .MuiOutlinedInput-root'],
            borderRadius: '0 4px 4px 0',
          },
          '& input::placeholder': { color: 'var(--text-dim)', opacity: 1 },
        }}
      />
    </Box>
  );
}

function SchemaArrayInput({
  fieldKey,
  arr,
  onChange,
}: {
  fieldKey: string;
  arr: string[];
  onChange: (val: string[]) => void;
}) {
  const [input, setInput] = useState('');
  const push = () => {
    if (!input.trim()) return;
    onChange([...arr, input.trim()]);
    setInput('');
  };
  return (
    <input
      id={`arr-input-${fieldKey}`}
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ',') {
          e.preventDefault();
          push();
        }
      }}
      onBlur={push}
      placeholder={arr.length === 0 ? 'Type item, press Enter…' : ''}
      style={{
        border: 'none',
        outline: 'none',
        background: 'transparent',
        color: 'var(--text-primary)',
        fontSize: '13px',
        flex: '1 1 60px',
        minWidth: 60,
        padding: '2px 0',
      }}
    />
  );
}

// ── Main component ──────────────────────────────────────────────────────
interface JsonFormRendererProps {
  parsedValue: Record<string, unknown>;
  readOnly: boolean;
  onUiChange: (key: string, val: unknown) => void;
  onAddKey: (key: string, val: unknown) => void;
  onRemoveKey: (key: string) => void;
  fieldSchema?: Record<string, PropSchema>;
}

export function JsonFormRenderer({
  parsedValue,
  readOnly,
  onUiChange,
  onAddKey,
  onRemoveKey,
  fieldSchema,
}: JsonFormRendererProps) {
  // Schema-driven mode: render only known keys, no add/delete
  if (fieldSchema) {
    const schemaEntries = Object.entries(fieldSchema);
    const hasAnyValue = schemaEntries.some(
      ([k]) => parsedValue[k] !== undefined && parsedValue[k] !== '' && parsedValue[k] !== null,
    );
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
        {schemaEntries.map(([key, propSchema]) => (
          <Box key={key}>
            <SchemaField
              fieldKey={key}
              propSchema={propSchema}
              value={parsedValue[key]}
              readOnly={readOnly}
              onChange={onUiChange}
            />
          </Box>
        ))}
        {!hasAnyValue && readOnly && (
          <Typography
            sx={{
              color: 'var(--text-dim)',
              fontSize: '13px',
              fontStyle: 'italic',
              py: 1,
            }}
          >
            Not set
          </Typography>
        )}
      </Box>
    );
  }

  const entries = Object.entries(parsedValue);

  const deleteBtn = (key: string, mt = 0) => (
    <Tooltip title="Remove key">
      <IconButton
        size="small"
        onClick={() => onRemoveKey(key)}
        sx={{
          color: 'var(--text-secondary)',
          mt,
          flexShrink: 0,
          '&:hover': { color: 'var(--text-primary)' },
        }}
      >
        <DeleteIcon sx={{ fontSize: 16 }} />
      </IconButton>
    </Tooltip>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
      {entries.map(([key, value]) => {
        const type = getDataType(value);
        const locked = isLockedValue(value);

        // ── Object ───────────────────────────────────────────────────
        if (type === 'object') {
          return (
            <Box key={key} sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-start' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <CollapsibleSection
                  label={key}
                  type="object"
                  rightSlot={!readOnly ? deleteBtn(key) : undefined}
                >
                  <JsonFormRenderer
                    parsedValue={value as Record<string, unknown>}
                    readOnly={readOnly}
                    onUiChange={(k, v) =>
                      onUiChange(key, {
                        ...(value as Record<string, unknown>),
                        [k]: v,
                      })
                    }
                    onAddKey={(k, v) =>
                      onUiChange(key, {
                        ...(value as Record<string, unknown>),
                        [k]: v,
                      })
                    }
                    onRemoveKey={(k) => {
                      const next = { ...(value as Record<string, unknown>) };
                      delete next[k];
                      onUiChange(key, next);
                    }}
                  />
                </CollapsibleSection>
              </Box>
            </Box>
          );
        }

        // ── Array ────────────────────────────────────────────────────
        if (type === 'array') {
          return (
            <Box key={key} sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-start' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <ArraySection
                  arrKey={key}
                  arr={value as unknown[]}
                  readOnly={readOnly}
                  onChange={(v) => onUiChange(key, v)}
                />
              </Box>
              {!readOnly && <Box sx={{ mt: 0.25 }}>{deleteBtn(key)}</Box>}
            </Box>
          );
        }

        // ── Boolean ──────────────────────────────────────────────────
        if (type === 'boolean') {
          if (readOnly) {
            return <PrimitiveReadOnlyRow key={key} fieldKey={key} value={value} type="boolean" />;
          }
          return (
            <Box
              key={key}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                px: 1.5,
                py: 1,
                bgcolor: 'var(--bg-secondary)',
                borderRadius: '0 4px 4px 0',
                borderLeft: `3px solid ${TYPE_META.boolean.line}`,
              }}
            >
              <Typography
                sx={{
                  fontSize: '10px',
                  fontWeight: 700,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  minWidth: 80,
                  flexShrink: 0,
                }}
              >
                {key}
              </Typography>
              <Box sx={{ flex: 1 }} />
              <ToggleButtonGroup
                size="small"
                exclusive
                value={value as boolean}
                onChange={(_, v) => {
                  if (v !== null) onUiChange(key, v);
                }}
                sx={{
                  '& .MuiToggleButton-root': {
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border)',
                    fontSize: '11px',
                    px: 1.5,
                    '&.Mui-selected': {
                      bgcolor: TYPE_META.boolean.fg,
                      color: '#fff',
                      borderColor: TYPE_META.boolean.fg,
                      '&:hover': { bgcolor: TYPE_META.boolean.fg },
                    },
                  },
                }}
              >
                <ToggleButton value={true}>True</ToggleButton>
                <ToggleButton value={false}>False</ToggleButton>
              </ToggleButtonGroup>
              <TypeBadge type="boolean" />
              {deleteBtn(key)}
            </Box>
          );
        }

        // ── Number ───────────────────────────────────────────────────
        if (type === 'number') {
          if (readOnly) {
            return <PrimitiveReadOnlyRow key={key} fieldKey={key} value={value} type="number" />;
          }
          return (
            <Box
              key={key}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                pl: 0,
                borderRadius: '0 4px 4px 0',
                borderLeft: `3px solid ${TYPE_META.number.line}`,
              }}
            >
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <TextField
                  size="small"
                  type="number"
                  fullWidth
                  label={key}
                  value={value as number}
                  onChange={(e) => onUiChange(key, parseFloat(e.target.value))}
                  slotProps={{
                    input: { endAdornment: <TypeBadge type="number" /> },
                    inputLabel: { shrink: true },
                  }}
                  sx={{
                    ...TEXT_FIELD_SX,
                    '& .MuiOutlinedInput-root': {
                      ...TEXT_FIELD_SX['& .MuiOutlinedInput-root'],
                      borderRadius: '0 4px 4px 0',
                    },
                  }}
                />
              </Box>
              {deleteBtn(key)}
            </Box>
          );
        }

        // ── String: LAUI ─────────────────────────────────────────────
        if (type === 'string' && isLauiKey(key, value)) {
          const itemType = getItemTypeFromKey(key);
          return (
            <Box key={key} sx={{ display: 'flex', gap: 0.5, alignItems: 'flex-start' }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  sx={{
                    fontSize: '10px',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--text-secondary)',
                    mb: 0.5,
                  }}
                >
                  {key}
                </Typography>
                <QuickSearch
                  label={key}
                  value={value as string}
                  filters={{ item_type: itemType }}
                  disambigField={itemType === 'task' ? 'partition' : undefined}
                  disabled={readOnly}
                  onSelect={(rawItem) => {
                    if (readOnly) return;
                    const raw = rawItem as Record<string, unknown>;
                    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                    onUiChange(key, laui);
                  }}
                  placeholder={`Search ${itemType}…`}
                />
              </Box>
              {!readOnly && <Box sx={{ mt: 3 }}>{deleteBtn(key)}</Box>}
            </Box>
          );
        }

        // ── String: plain / locked ────────────────────────────────────
        if (readOnly) {
          return <PrimitiveReadOnlyRow key={key} fieldKey={key} value={value} type="string" />;
        }
        return (
          <Box
            key={key}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              borderRadius: '0 4px 4px 0',
              borderLeft: `3px solid ${TYPE_META.string.line}`,
            }}
          >
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <TextField
                size="small"
                fullWidth
                label={key}
                value={value as string}
                onChange={(e) => !locked && onUiChange(key, e.target.value)}
                disabled={locked}
                slotProps={{
                  input: {
                    endAdornment: locked ? (
                      <LockIcon
                        sx={{
                          fontSize: 15,
                          color: 'var(--text-secondary)',
                          mr: -0.5,
                        }}
                      />
                    ) : (
                      <TypeBadge type="string" />
                    ),
                  },
                  inputLabel: { shrink: true },
                }}
                sx={{
                  ...TEXT_FIELD_SX,
                  '& .MuiOutlinedInput-root': {
                    ...TEXT_FIELD_SX['& .MuiOutlinedInput-root'],
                    borderRadius: '0 4px 4px 0',
                  },
                }}
              />
            </Box>
            {!locked && deleteBtn(key)}
          </Box>
        );
      })}

      {/* Empty state */}
      {entries.length === 0 && (
        <Typography sx={{ color: 'var(--text-dim)', fontSize: '13px', fontStyle: 'italic', py: 1 }}>
          No fields yet. Add a key below.
        </Typography>
      )}

      {/* Add key row */}
      {!readOnly && <AddKeyRow onAdd={onAddKey} />}
    </Box>
  );
}
