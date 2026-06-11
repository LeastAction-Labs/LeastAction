/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import {
  Box,
  Chip,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';

import MarkdownRenderer from '@/components/browse/MarkdownRenderer';
import { MonacoWrapper, TabPanel } from '@/components/ui';

import type { ArrayItem } from './types';

interface ViewModeRendererProps {
  field: any;
  value: any;
  arrayValue: ArrayItem[];
  shouldUseArrayFormat: boolean;
  shouldUseMonaco: boolean;
  shouldUseTextarea: boolean;
  itemData: any;
}

const styles = {
  emptyText: {
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },
  arrayFieldContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  arrayTabsContainer: {
    border: 1,
    borderColor: 'var(--border)',
    borderRadius: 1,
  },
  arrayTabs: {
    minHeight: '32px',
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none',
      fontSize: '12px',
      fontWeight: 400,
      minHeight: '32px',
      minWidth: 'auto',
      px: 1,
      py: 0,
      '&.Mui-selected': {
        color: 'var(--accent)',
        fontWeight: 600,
      },
    },
    '& .MuiTabs-indicator': {
      bgcolor: 'var(--accent)',
      height: '2px',
    },
  },
  viewModeContainer: {
    backgroundColor: 'var(--bg-tertiary)',
    p: 1,
    borderRadius: 1,
    border: '1px solid var(--border)',
  },
  fileLabel: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    mb: 0.5,
    fontFamily: 'monospace',
  },
  csvTableContainer: {
    maxHeight: 400,
    border: '1px solid var(--border)',
    borderRadius: 1,
  },
  csvTableHead: {
    backgroundColor: 'var(--bg-secondary)',
    '& .MuiTableCell-head': {
      fontWeight: 600,
      fontSize: '12px',
      color: 'var(--text-primary)',
      borderBottom: '2px solid var(--border)',
    },
  },
  csvTableCell: {
    fontSize: '12px',
    color: 'var(--text-primary)',
    borderBottom: '1px solid var(--border)',
    py: 1,
    px: 2,
  },
  csvTableRow: {
    '&:nth-of-type(even)': {
      backgroundColor: 'var(--bg-tertiary)',
    },
    '&:hover': {
      backgroundColor: 'var(--bg-hover)',
    },
  },
};

// Helper function to count field delimiters (commas outside quotes)
const countFields = (line: string): number => {
  let fieldCount = 1; // Start with 1 (first field before any comma)
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      // Handle escaped quotes
      if (inQuotes && line[i + 1] === '"') {
        i++; // Skip the next quote
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      fieldCount++;
    }
  }

  return fieldCount;
};

// Helper function to detect if content is CSV
const isCSV = (content: string): boolean => {
  if (!content || typeof content !== 'string') return false;

  const lines = content.trim().split('\n');
  if (lines.length < 2) return false; // Need at least header + 1 data row

  // Check if first line looks like a header (has commas)
  const firstLine = lines[0];
  if (!firstLine.includes(',')) return false;

  // Count fields (not just commas) to handle quoted fields with commas
  const firstLineFields = countFields(firstLine);

  // Check if rows have consistent field count
  const consistentFields = lines.slice(0, Math.min(5, lines.length)).every((line) => {
    const fieldCount = countFields(line);
    return fieldCount === firstLineFields;
  });

  return consistentFields;
};

// Helper function to parse CSV
const parseCSV = (csv: string): { headers: string[]; rows: string[][] } => {
  const lines = csv.trim().split('\n');
  if (lines.length === 0) return { headers: [], rows: [] };

  const parseLine = (line: string): string[] => {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current.trim());

    return result;
  };

  const headers = parseLine(lines[0]);
  const rows = lines.slice(1).map((line) => parseLine(line));

  return { headers, rows };
};

// CSV Table Component
const CSVTable = ({ content }: { content: string }) => {
  const { headers, rows } = parseCSV(content);

  return (
    <TableContainer component={Paper} sx={styles.csvTableContainer}>
      <Table stickyHeader size="small">
        <TableHead sx={styles.csvTableHead}>
          <TableRow>
            {headers.map((header, index) => (
              <TableCell key={index}>{header}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex} sx={styles.csvTableRow}>
              {row.map((cell, cellIndex) => (
                <TableCell key={cellIndex} sx={styles.csvTableCell}>
                  {cell}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Box
        sx={{
          p: 1,
          backgroundColor: 'var(--bg-secondary)',
          borderTop: '1px solid var(--border)',
        }}
      >
        <Typography variant="caption" sx={{ color: 'var(--text-secondary)' }}>
          {rows.length} rows
        </Typography>
      </Box>
    </TableContainer>
  );
};

// ── S3 / Hive partition path renderer ────────────────────────────────────────

function S3PathDisplay({ path }: Readonly<{ path: string }>) {
  // Split into: protocol+bucket prefix  vs  the rest
  const prefixMatch = path.match(/^([a-z0-9+.-]+:\/\/[^/]*\/)/);
  const prefix = prefixMatch ? prefixMatch[1] : '';
  const rest = path.slice(prefix.length);
  const trailingSlash = rest.endsWith('/') && rest.length > 1;
  const segments = rest.replace(/\/$/, '').split('/').filter(Boolean);

  return (
    <Box
      sx={{
        fontFamily: 'monospace',
        fontSize: '12px',
        bgcolor: 'var(--bg-tertiary)',
        border: '1px solid var(--border)',
        borderRadius: 1,
        px: 1.25,
        py: 0.75,
        display: 'inline-flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        maxWidth: '100%',
        wordBreak: 'break-all',
        lineHeight: 1.9,
      }}
    >
      {prefix && (
        <Box component="span" sx={{ color: 'var(--text-secondary)' }}>
          {prefix}
        </Box>
      )}
      {segments.map((seg, i) => {
        const eqIdx = seg.indexOf('=');
        const isPartition = eqIdx > 0;
        const isLast = i === segments.length - 1;
        return (
          <Box component="span" key={i} sx={{ display: 'inline-flex', alignItems: 'center' }}>
            {isPartition ? (
              <>
                <Box component="span" sx={{ color: 'var(--accent)', fontWeight: 600 }}>
                  {seg.slice(0, eqIdx + 1)}
                </Box>
                <Box component="span" sx={{ color: 'var(--text-primary)' }}>
                  {seg.slice(eqIdx + 1)}
                </Box>
              </>
            ) : (
              <Box component="span" sx={{ color: 'var(--text-primary)' }}>
                {seg}
              </Box>
            )}
            {(!isLast || trailingSlash) && (
              <Box component="span" sx={{ color: 'var(--text-secondary)', mx: 0.1 }}>
                /
              </Box>
            )}
          </Box>
        );
      })}
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

export const ViewModeRenderer = ({
  field,
  value,
  arrayValue,
  shouldUseArrayFormat,
  shouldUseMonaco,
  itemData,
}: ViewModeRendererProps) => {
  const [viewTabValue, setViewTabValue] = useState(0);

  // viewerType is an explicit rendering override — always takes priority over array format
  if (field.viewerType === 'markdown' && !shouldUseArrayFormat) {
    const content = typeof value === 'string' ? value : '';
    if (!content) {
      return (
        <Typography sx={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '12px' }}>
          No content available
        </Typography>
      );
    }
    return (
      <MarkdownRenderer
        content={content}
        containerSx={{ p: 0, maxWidth: 'unset', mx: 0, fontFamily: 'inherit' }}
      />
    );
  }

  if (shouldUseArrayFormat) {
    if (arrayValue.length === 0) {
      return (
        <Box component="span" sx={styles.emptyText}>
          No items
        </Box>
      );
    }

    if (arrayValue.length > 1) {
      const handleViewTabChange = (_event: React.SyntheticEvent, newValue: number) => {
        setViewTabValue(newValue);
      };

      return (
        <Box sx={styles.arrayFieldContainer}>
          <Box sx={styles.arrayTabsContainer}>
            <Tabs
              value={viewTabValue}
              onChange={handleViewTabChange}
              variant="scrollable"
              scrollButtons="auto"
              sx={styles.arrayTabs}
            >
              {arrayValue.map((item: ArrayItem, index: number) => (
                <Tab key={index} label={item.fileName} sx={{ fontSize: '12px !important' }} />
              ))}
            </Tabs>

            {arrayValue.map((item: ArrayItem, index: number) => (
              <TabPanel key={index} value={viewTabValue} index={index}>
                {field.viewerType === 'markdown' ? (
                  item.content ? (
                    <MarkdownRenderer
                      content={typeof item.content === 'string' ? item.content : ''}
                      containerSx={{
                        p: 0,
                        maxWidth: 'unset',
                        mx: 0,
                        fontFamily: 'inherit',
                      }}
                    />
                  ) : (
                    <Typography
                      sx={{
                        color: 'var(--text-secondary)',
                        fontStyle: 'italic',
                        fontSize: '12px',
                      }}
                    >
                      No content available
                    </Typography>
                  )
                ) : isCSV(item.content) ? (
                  <CSVTable content={item.content} />
                ) : (
                  <MonacoWrapper
                    content={item.content}
                    fileName={item.fileName}
                    readOnly={true}
                    field={field}
                  />
                )}
              </TabPanel>
            ))}
          </Box>
        </Box>
      );
    }

    return (
      <Box sx={styles.arrayFieldContainer}>
        {arrayValue.map((item: ArrayItem, index: number) => (
          <Box key={index} sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={styles.fileLabel}>
              📄 {item.fileName}
            </Typography>
            {isCSV(item.content) ? (
              <CSVTable content={item.content} />
            ) : (
              <MonacoWrapper
                content={item.content}
                fileName={item.fileName}
                readOnly={true}
                field={field}
              />
            )}
          </Box>
        ))}
      </Box>
    );
  }

  if (shouldUseMonaco) {
    // Format content for Monaco or CSV
    let monacoContent = '';

    if (typeof value === 'object' && value !== null) {
      // If value is an object, stringify it with formatting
      monacoContent = JSON.stringify(value, null, 2);
    } else if (typeof value === 'string' && value.trim()) {
      // Check if it's CSV first
      if (isCSV(value)) {
        return <CSVTable content={value} />;
      }

      // If value is a string, try to parse and reformat as JSON
      try {
        const parsed = JSON.parse(value);
        monacoContent = JSON.stringify(parsed, null, 2);
      } catch {
        // If not valid JSON, use as-is
        monacoContent = value;
      }
    } else {
      monacoContent = value || '';
    }

    return (
      <MonacoWrapper
        content={monacoContent}
        fileName={itemData.name}
        readOnly={true}
        field={field}
      />
    );
  }

  // Boolean — Yes/No chip
  if (field.datatype === 'boolean') {
    return (
      <Chip
        label={value ? 'Yes' : 'No'}
        size="small"
        sx={{
          bgcolor: value ? 'var(--success-subtle, rgba(76,175,80,0.12))' : 'var(--bg-tertiary)',
          color: 'var(--text-primary)',
          fontWeight: 500,
        }}
      />
    );
  }

  // Array of strings — chip list (e.g. tags)
  if (field.datatype === 'array' && field.items === 'string') {
    const items: string[] = Array.isArray(value) ? value : [];
    if (items.length === 0) {
      return <Typography sx={{ ...styles.emptyText, fontSize: '14px' }}>No items</Typography>;
    }
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {items.map((tag) => (
          <Chip
            key={tag}
            label={tag}
            size="small"
            sx={{
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
            }}
          />
        ))}
      </Box>
    );
  }

  // S3 / cloud storage path — styled with highlighted hive partitions
  if (typeof value === 'string' && /^(s3a?|gs|hdfs|abfs):\/\//.test(value)) {
    return <S3PathDisplay path={value} />;
  }

  // Plain text / number — no box, just clean typography
  return (
    <Typography
      sx={{
        fontSize: '14px',
        color: 'var(--text-primary)',
        whiteSpace: 'pre-wrap',
        lineHeight: '1.5',
        fontFamily: 'inherit',
      }}
    >
      {typeof value === 'object' && value !== null
        ? JSON.stringify(value, null, 2)
        : (value ?? (
            <Box component="span" sx={styles.emptyText}>
              No value
            </Box>
          ))}
    </Typography>
  );
};
