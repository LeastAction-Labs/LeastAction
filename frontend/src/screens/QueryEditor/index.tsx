/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';

import MarkdownRenderer from '@/components/browse/MarkdownRenderer';
import { MonacoWrapper } from '@/components/ui/MonacoWrapper';
import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { searchCatalogItems } from '@/services/catalog.service';
import { type QueryResult, executeQuery } from '@/services/query.service';

const QUERY_CHEAT_SHEET = `
## Query Examples

#### connection.postgresql / connection.mysql
\`\`\`sql
SELECT * FROM my_table ORDER BY created_at DESC LIMIT 20;
SELECT COUNT(*) FROM my_table WHERE date_col = '2026-05-26';
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'my_table';
SELECT id, COUNT(*) FROM my_table GROUP BY id HAVING COUNT(*) > 1;
\`\`\`

#### connection.AWS — Athena / Redshift / S3
\`\`\`sql
-- Athena: filter on partition column
SELECT COUNT(*) FROM my_db.my_table WHERE dt = '2026-05-26';
DESCRIBE my_db.my_table;
-- S3 parquet (no output_location in connection)
SELECT * FROM read_parquet('s3://my-bucket/data/orders/*.parquet') LIMIT 50;
DESCRIBE SELECT * FROM read_parquet('s3://my-bucket/data/file.parquet');
-- S3 CSV — auto_detect handles delimiter, header, and types
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true) LIMIT 20;
DESCRIBE SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv', auto_detect=true);
-- explicit types if auto_detect gets it wrong
SELECT * FROM read_csv('s3://my-bucket/raw/orders.csv',
  header=true, columns={'order_id':'VARCHAR','amount':'DOUBLE'}) LIMIT 20;
\`\`\`

#### connection.gcp — BigQuery / GCS
\`\`\`sql
-- BigQuery (connection has project field)
SELECT * FROM \`project.dataset.my_table\` WHERE DATE(_PARTITIONTIME) = '2026-05-26' LIMIT 20;
-- GCS via DuckDB (connection has HMAC keys, no project)
SELECT * FROM read_parquet('gs://my-bucket/data/orders/*.parquet') LIMIT 50;
SELECT * FROM read_csv('gs://my-bucket/raw/orders.csv', header=true) LIMIT 20;
\`\`\`

#### connection.azure — Blob Storage
\`\`\`sql
SELECT * FROM read_parquet('azure://my-container/data/orders/*.parquet') LIMIT 50;
DESCRIBE SELECT * FROM read_parquet('azure://my-container/data/file.parquet');
\`\`\`

> Max **10,000 rows** · Timeout **2 min** · Read-only (SELECT / WITH / EXPLAIN only)
`.trim();

interface Connection {
  laui: string;
  name: string;
  item_type: string;
}

const SUPPORTED_TYPES = ['connection'];

export default function QueryEditor() {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedConn, setSelectedConn] = useState<string>('');
  const [sql, setSql] = useState('SELECT 1');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingConns, setLoadingConns] = useState(true);
  const tableRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchConnections = async () => {
      try {
        const results = await Promise.all(
          SUPPORTED_TYPES.map((t) =>
            searchCatalogItems(t, false, {
              perPage: 100,
              projection: ['name', 'item_type'],
            }),
          ),
        );
        const all: Connection[] = results.flatMap((r) =>
          (r.items ?? []).map((raw: any) => {
            const item = raw.item || raw;
            return {
              laui: item._laui || item.laui,
              name: item.name || 'Unnamed',
              item_type: item.item_type || '',
            };
          }),
        );
        setConnections(all);
        if (all.length) setSelectedConn(all[0].laui);
      } catch {
        // silent
      } finally {
        setLoadingConns(false);
      }
    };
    void fetchConnections();
  }, []);

  const handleRun = async () => {
    if (!selectedConn || !sql.trim()) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await executeQuery(selectedConn, sql.trim());
      setResult(res);
      setTimeout(() => tableRef.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Query failed.');
    } finally {
      setRunning(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') void handleRun();
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'var(--bg-primary)',
        overflow: 'hidden',
      }}
    >
      {/* Toolbar */}
      <Box
        sx={{
          px: 2,
          py: 1,
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          borderBottom: '1px solid var(--border)',
          bgcolor: 'var(--bg-secondary)',
          flexShrink: 0,
        }}
      >
        <Box>
          <Typography
            sx={{
              fontSize: FONT_SIZES.SM,
              fontWeight: FONT_WEIGHTS.WEIGHT_600,
              color: 'var(--text-primary)',
            }}
          >
            Data Inspector
          </Typography>
          <Typography
            sx={{
              fontSize: '0.62rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.2,
            }}
          >
            Verification tool used by the AI — debug surface for engineers
          </Typography>
        </Box>
        <Chip
          label="Experimental Preview"
          size="small"
          sx={{
            height: 18,
            fontSize: '0.62rem',
            fontWeight: 600,
            bgcolor: 'var(--accent, #7c3aed)',
            color: '#fff',
            letterSpacing: '0.03em',
          }}
        />

        <FormControl size="small" sx={{ minWidth: 240 }} disabled={loadingConns}>
          <InputLabel sx={{ fontSize: '0.75rem' }}>Connection</InputLabel>
          <Select
            label="Connection"
            value={selectedConn}
            onChange={(e) => setSelectedConn(e.target.value)}
            sx={{ fontSize: '0.78rem' }}
          >
            {connections.length === 0 && (
              <MenuItem value="" disabled>
                {loadingConns ? 'Loading…' : 'No connections found'}
              </MenuItem>
            )}
            {connections.map((c) => {
              const subtype = c.item_type.startsWith('connection.')
                ? c.item_type.slice('connection.'.length)
                : null;
              return (
                <MenuItem
                  key={c.laui}
                  value={c.laui}
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <span style={{ flex: 1 }}>{c.name}</span>
                  {subtype ? (
                    <span
                      style={{
                        fontSize: '0.65rem',
                        color: 'var(--text-secondary)',
                        fontFamily: 'monospace',
                        flexShrink: 0,
                      }}
                    >
                      {subtype}
                    </span>
                  ) : (
                    <span
                      style={{
                        fontSize: '0.65rem',
                        color: '#f59e0b',
                        flexShrink: 0,
                      }}
                    >
                      no subtype
                    </span>
                  )}
                </MenuItem>
              );
            })}
          </Select>
          <FormHelperText sx={{ fontSize: '0.6rem', mx: 0, mt: 0.5 }}>
            Must have a subtype e.g. connection.postgresql
          </FormHelperText>
        </FormControl>

        <Button
          variant="contained"
          size="small"
          startIcon={
            running ? (
              <CircularProgress size={14} color="inherit" />
            ) : (
              <PlayArrowIcon sx={{ fontSize: 16 }} />
            )
          }
          onClick={() => void handleRun()}
          disabled={running || !selectedConn || !sql.trim()}
          sx={{
            textTransform: 'none',
            fontSize: '0.75rem',
            bgcolor: 'var(--accent)',
            '&:hover': { bgcolor: 'var(--accent-hover, #7c3aed)' },
            '&:disabled': { opacity: 0.5 },
          }}
        >
          {running ? 'Running…' : 'Run'}
        </Button>

        <Typography sx={{ fontSize: '0.68rem', color: 'var(--text-secondary)', ml: 'auto' }}>
          ⌘ + Enter to run
        </Typography>
      </Box>

      {/* Editor */}
      <Box
        sx={{
          flex: '0 0 280px',
          borderBottom: '1px solid var(--border)',
          overflow: 'hidden',
        }}
      >
        <MonacoWrapper
          content={sql}
          fileName="query.sql"
          field={{ fontSize: 13, minimap: false, wordWrap: 'on', lineNumbers: 'on' }}
          onChange={(v) => setSql(v ?? '')}
          height="280px"
        />
      </Box>

      {/* Results */}
      <Box ref={tableRef} sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2, fontSize: '0.78rem' }}>
            {error}
          </Alert>
        )}

        {result && (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Typography
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Results
              </Typography>
              <Chip
                label={`${result.row_count} row${result.row_count !== 1 ? 's' : ''}`}
                size="small"
                sx={{
                  height: 18,
                  fontSize: '0.65rem',
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-secondary)',
                }}
              />
            </Box>

            {result.columns.length === 0 ? (
              <Typography sx={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Query executed successfully (no rows returned).
              </Typography>
            ) : (
              <Box
                sx={{
                  overflow: 'auto',
                  border: '1px solid var(--border)',
                  borderRadius: 1,
                }}
              >
                <table
                  style={{
                    borderCollapse: 'collapse',
                    width: '100%',
                    fontSize: '0.75rem',
                  }}
                >
                  <thead>
                    <tr style={{ background: 'var(--bg-secondary)' }}>
                      {result.columns.map((col) => (
                        <th
                          key={col}
                          style={{
                            padding: '6px 10px',
                            textAlign: 'left',
                            borderBottom: '1px solid var(--border)',
                            color: 'var(--text-secondary)',
                            fontWeight: 600,
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, ri) => (
                      <tr
                        key={ri}
                        style={{
                          background: ri % 2 === 0 ? 'var(--bg-primary)' : 'var(--bg-secondary)',
                        }}
                      >
                        {row.map((cell, ci) => (
                          <td
                            key={ci}
                            style={{
                              padding: '5px 10px',
                              borderBottom: '1px solid var(--border)',
                              color: 'var(--text-primary)',
                              maxWidth: 320,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {cell === null ? (
                              <span
                                style={{
                                  color: 'var(--text-secondary)',
                                  fontStyle: 'italic',
                                }}
                              >
                                null
                              </span>
                            ) : typeof cell === 'object' ? (
                              JSON.stringify(cell)
                            ) : (
                              `${cell as string | number | boolean}`
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Box>
            )}
          </>
        )}

        {!error && !result && !running && (
          <MarkdownRenderer
            content={QUERY_CHEAT_SHEET}
            containerSx={{ p: 0, maxWidth: '100%', mx: 0 }}
          />
        )}
      </Box>
    </Box>
  );
}
