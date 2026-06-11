/**
 * PerformanceDashboard.jsx
 *
 * Dynamic query-driven dashboard backed by DuckDB-WASM.
 * Each panel has its own SQL, chart type, and column config — all editable.
 * Pre-filled panels mirror the Python performance_analysis.py report exactly.
 * Panels are persisted to localStorage.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';

import * as duckdb from '@duckdb/duckdb-wasm';
import Editor from '@monaco-editor/react';
import {
  Add as AddIcon,
  BarChart as BarChartIcon,
  ExpandLess as CollapseIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandIcon,
  RestartAlt as ResetIcon,
  PlayArrow as RunIcon,
  Code as SqlIcon,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Divider,
  FormControl,
  FormControlLabel,
  FormLabel,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { BarChart, LineChart } from '@mui/x-charts';

// ─── Constants ────────────────────────────────────────────────────────────────
const CHART_COLORS = [
  '#667eea',
  '#e05c5c',
  '#36b37e',
  '#f59e0b',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
  '#84cc16',
  '#f97316',
  '#14b8a6',
  '#a78bfa',
  '#fb923c',
  '#34d399',
  '#60a5fa',
  '#f472b6',
  '#facc15',
  '#4ade80',
  '#38bdf8',
  '#c084fc',
  '#fb7185',
];
const STORAGE_KEY = 'perf_dashboard_panels_v1';

// ─── Default panels (pre-filled from Python script) ───────────────────────────
const DEFAULT_PANELS = [
  {
    id: 'slowest',
    title: '🐌 Top 30 Slowest Functions',
    chartType: 'table',
    sql: `SELECT
  function_name,
  ROUND(AVG(duration_ms), 2)    AS mean_ms,
  ROUND(MEDIAN(duration_ms), 2) AS median_ms,
  ROUND(MAX(duration_ms), 2)    AS max_ms,
  COUNT(*)                      AS calls
FROM perf_data
GROUP BY function_name
ORDER BY max_ms DESC
LIMIT 30`,
    xColumn: 'function_name',
    yColumns: ['max_ms'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'most_called',
    title: '🔥 Most Called Functions',
    chartType: 'bar',
    sql: `SELECT function_name, COUNT(*) AS calls
FROM perf_data
GROUP BY function_name
ORDER BY calls DESC
LIMIT 30`,
    xColumn: 'function_name',
    yColumns: ['calls'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'top_errors',
    title: '🚨 Top APIs by Error Count',
    chartType: 'table',
    sql: `SELECT
  e.function_name,
  e.error_count,
  t.total_count,
  ROUND(e.error_count * 100.0 / t.total_count, 2) AS error_rate_pct
FROM (SELECT function_name, COUNT(*) AS error_count
      FROM perf_data WHERE has_error GROUP BY function_name) e
JOIN (SELECT function_name, COUNT(*) AS total_count
      FROM perf_data GROUP BY function_name) t
  ON e.function_name = t.function_name
ORDER BY e.error_count DESC
LIMIT 10`,
    xColumn: 'function_name',
    yColumns: ['error_count'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'calls_by_hour',
    title: '📊 Calls by Hour',
    chartType: 'bar',
    sql: `SELECT HOUR(timestamp) AS hour, COUNT(*) AS calls
FROM perf_data
GROUP BY hour ORDER BY hour`,
    xColumn: 'hour',
    yColumns: ['calls'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'duration_by_hour',
    title: '⏱ Avg Duration by Hour',
    chartType: 'bar',
    sql: `SELECT HOUR(timestamp) AS hour, ROUND(AVG(duration_ms), 2) AS avg_ms
FROM perf_data
GROUP BY hour ORDER BY hour`,
    xColumn: 'hour',
    yColumns: ['avg_ms'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'errors_by_hour',
    title: '🚨 Errors by Hour',
    chartType: 'bar',
    sql: `SELECT HOUR(timestamp) AS hour, COUNT(*) AS error_count
FROM perf_data WHERE has_error
GROUP BY hour ORDER BY hour`,
    xColumn: 'hour',
    yColumns: ['error_count'],
    seriesColumn: '',
    enabled: true,
  },
  {
    id: 'ts_mean',
    title: '📈 Mean Duration (15-min intervals)',
    chartType: 'line',
    sql: `SELECT
  strftime('%Y-%m-%d %H:%M', to_timestamp((epoch(timestamp)::BIGINT / 900) * 900)::TIMESTAMP) AS time_bucket,
  function_name,
  ROUND(AVG(duration_ms), 2) AS mean_ms
FROM perf_data
WHERE timestamp IS NOT NULL
GROUP BY time_bucket, function_name
ORDER BY time_bucket`,
    xColumn: 'time_bucket',
    yColumns: ['mean_ms'],
    seriesColumn: 'function_name',
    enabled: true,
  },
  {
    id: 'ts_max',
    title: '📈 Max Duration (15-min intervals)',
    chartType: 'line',
    sql: `SELECT
  strftime('%Y-%m-%d %H:%M', to_timestamp((epoch(timestamp)::BIGINT / 900) * 900)::TIMESTAMP) AS time_bucket,
  function_name,
  ROUND(MAX(duration_ms), 2) AS max_ms
FROM perf_data
WHERE timestamp IS NOT NULL
GROUP BY time_bucket, function_name
ORDER BY time_bucket`,
    xColumn: 'time_bucket',
    yColumns: ['max_ms'],
    seriesColumn: 'function_name',
    enabled: true,
  },
  {
    id: 'ts_min',
    title: '📈 Min Duration (15-min intervals)',
    chartType: 'line',
    sql: `SELECT
  strftime('%Y-%m-%d %H:%M', to_timestamp((epoch(timestamp)::BIGINT / 900) * 900)::TIMESTAMP) AS time_bucket,
  function_name,
  ROUND(MIN(duration_ms), 2) AS min_ms
FROM perf_data
WHERE timestamp IS NOT NULL
GROUP BY time_bucket, function_name
ORDER BY time_bucket`,
    xColumn: 'time_bucket',
    yColumns: ['min_ms'],
    seriesColumn: 'function_name',
    enabled: true,
  },
];

// ─── DuckDB singleton ─────────────────────────────────────────────────────────
let _db = null;
let _dataLoaded = false; // tracks whether perf_data table is ready in this session

async function getDB() {
  if (_db) return _db;
  const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles());
  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker}");`], { type: 'text/javascript' }),
  );
  const worker = new Worker(workerUrl);
  const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);
  _db = db;
  return db;
}

/** Convert an Arrow query result to plain JS objects */
function arrowToRows(table) {
  const fields = table.schema.fields.map((f) => f.name);
  return table.toArray().map((row) => {
    const obj = {};
    fields.forEach((f) => {
      const v = row[f];
      obj[f] = typeof v === 'bigint' ? Number(v) : v;
    });
    return obj;
  });
}

/** Ingest log files and create the perf_data table */
async function loadPerfData(dateMode, date, startDate, endDate) {
  const db = await getDB();
  const conn = await db.connect();

  // Fetch file list from Vite dev middleware
  const relPaths = await fetch('/api/perf-logs/list').then((r) => {
    if (!r.ok)
      throw new Error(`Cannot list log files (${r.status}). Is the Vite dev server running?`);
    return r.json();
  });
  if (!relPaths.length) throw new Error('No .log files found under logs/category=PERFORMANCE/');

  // Register each file in DuckDB virtual FS with its hive path
  await Promise.all(
    relPaths.map(async (rel) => {
      const buf = await fetch(`/api/perf-logs/file?p=${encodeURIComponent(rel)}`).then((r) =>
        r.arrayBuffer(),
      );
      await db.registerFileBuffer(`category=PERFORMANCE/${rel}`, new Uint8Array(buf));
    }),
  );

  const fileList = relPaths.map((r) => `'category=PERFORMANCE/${r}'`).join(', ');

  // Date filter (exact logic from Python script)
  let dateFilter = '';
  if (dateMode === 'single' && date) {
    const [y, m, d] = date.split('-');
    dateFilter = `WHERE yyyy = '${y}' AND mm = '${m}' AND dd = '${d}'`;
  } else if (dateMode === 'range' && startDate && endDate) {
    dateFilter = `WHERE make_date(CAST(yyyy AS INTEGER), CAST(mm AS INTEGER), CAST(dd AS INTEGER))
      BETWEEN DATE '${startDate}' AND DATE '${endDate}'`;
  }

  // Create perf_data (exact ingestion SQL from Python)
  await conn.query(`
    CREATE OR REPLACE TABLE perf_data AS
    SELECT
      timestamp::TIMESTAMP AS timestamp,
      operation            AS function_name,
      CASE WHEN message LIKE '{%' THEN TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)
           ELSE TRY_CAST(message AS DOUBLE) END AS execution_time_seconds,
      CASE WHEN message LIKE '{%' THEN json_extract_string(message, '$.error') IS NOT NULL
           ELSE FALSE END AS has_error,
      CASE WHEN message LIKE '{%' THEN json_extract_string(message, '$.error')
           ELSE NULL END AS error_detail,
      session_id, category, level,
      CASE WHEN message LIKE '{%' THEN TRY_CAST(json_extract_string(message, '$.execution_time') AS DOUBLE)
           ELSE TRY_CAST(message AS DOUBLE) END * 1000 AS duration_ms
    FROM read_json([${fileList}], format='newline_delimited', hive_partitioning=true, ignore_errors=true)
    ${dateFilter}
  `);

  // Compute summary stats
  const sr = arrowToRows(
    await conn.query(`
    SELECT
      COUNT(*) AS total_calls,
      AVG(duration_ms) AS avg_ms,
      MEDIAN(duration_ms) AS median_ms,
      QUANTILE_CONT(duration_ms, 0.95) AS p95_ms,
      QUANTILE_CONT(duration_ms, 0.99) AS p99_ms,
      MAX(duration_ms) AS max_ms,
      SUM(CASE WHEN has_error THEN 1 ELSE 0 END) AS total_errors
    FROM perf_data
  `),
  )[0];

  await conn.close();
  _dataLoaded = true;
  return sr;
}

/** Run a single panel's SQL against perf_data */
async function runPanelSQL(sql) {
  const db = await getDB();
  const conn = await db.connect();
  try {
    const table = await conn.query(sql);
    const columns = table.schema.fields.map((f) => f.name);
    const rows = arrowToRows(table);
    return { columns, rows, error: null };
  } catch (e) {
    return { columns: [], rows: [], error: e.message };
  } finally {
    await conn.close();
  }
}

// ─── Chart renderers ──────────────────────────────────────────────────────────
function TableOutput({ columns, rows }) {
  if (!rows.length)
    return (
      <Typography variant="caption" color="text.secondary">
        No rows returned.
      </Typography>
    );
  return (
    <TableContainer sx={{ maxHeight: 380 }}>
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {columns.map((c) => (
              <TableCell
                key={c}
                sx={{
                  fontWeight: 700,
                  color: '#667eea',
                  bgcolor: 'background.paper',
                }}
              >
                {c}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={i} hover>
              {columns.map((c) => (
                <TableCell key={c}>{row[c] != null ? String(row[c]) : '—'}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function BarOutput({ rows, xColumn, yColumns }) {
  if (!rows.length || !xColumn || !yColumns.length)
    return (
      <Typography variant="caption" color="text.secondary">
        Configure x/y columns above.
      </Typography>
    );
  const labels = rows.map((r) => String(r[xColumn] ?? ''));
  const series = yColumns.map((col, i) => ({
    data: rows.map((r) => Number(r[col]) || 0),
    label: col,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));
  return (
    <BarChart
      xAxis={[
        {
          scaleType: 'band',
          data: labels,
          tickLabelStyle: { fontSize: 10, angle: labels.length > 15 ? -45 : 0 },
        },
      ]}
      series={series}
      height={300}
      margin={{ bottom: labels.length > 15 ? 80 : 40 }}
    />
  );
}

function LineOutput({ rows, xColumn, yColumns, seriesColumn }) {
  if (!rows.length || !xColumn)
    return (
      <Typography variant="caption" color="text.secondary">
        Configure x column above.
      </Typography>
    );

  let labels, series;

  if (seriesColumn) {
    // Pivot: one series per unique seriesColumn value
    labels = [...new Set(rows.map((r) => String(r[xColumn] ?? '')))].sort();
    const seriesValues = [...new Set(rows.map((r) => String(r[seriesColumn] ?? '')))].sort();
    const yCol = yColumns[0] || '';
    const lookup = {};
    rows.forEach((r) => {
      const sv = String(r[seriesColumn]);
      if (!lookup[sv]) lookup[sv] = {};
      lookup[sv][String(r[xColumn])] = Number(r[yCol]) || null;
    });
    series = seriesValues.slice(0, 20).map((sv, i) => ({
      data: labels.map((x) => lookup[sv]?.[x] ?? null),
      label: sv,
      color: CHART_COLORS[i % CHART_COLORS.length],
      connectNulls: true,
      showMark: false,
    }));
  } else {
    // Direct: each y column is a series
    labels = rows.map((r) => String(r[xColumn] ?? ''));
    series = yColumns.map((col, i) => ({
      data: rows.map((r) => Number(r[col]) || null),
      label: col,
      color: CHART_COLORS[i % CHART_COLORS.length],
      connectNulls: true,
      showMark: false,
    }));
  }

  if (!series.length)
    return (
      <Typography variant="caption" color="text.secondary">
        Configure y column above.
      </Typography>
    );

  return (
    <LineChart
      xAxis={[
        {
          scaleType: 'band',
          data: labels,
          tickLabelStyle: { fontSize: 10, angle: -45 },
          tickMinStep: Math.ceil(labels.length / 20),
        },
      ]}
      yAxis={[{ min: 0 }]}
      series={series}
      height={400}
      sx={{ '& .MuiLineElement-root': { strokeWidth: 1.5 } }}
      slotProps={{
        legend: {
          position: { vertical: 'middle', horizontal: 'right' },
          itemMarkWidth: 10,
          itemMarkHeight: 10,
        },
      }}
    />
  );
}

function PanelOutput({ panel, result }) {
  if (!result) return null;
  if (result.loading)
    return (
      <Box sx={{ py: 2, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress size={24} />
      </Box>
    );
  if (result.error)
    return (
      <Alert severity="error" sx={{ mt: 1 }}>
        <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>{result.error}</pre>
      </Alert>
    );
  if (!result.rows.length)
    return (
      <Alert severity="info" sx={{ mt: 1 }}>
        No rows returned.
      </Alert>
    );

  if (panel.chartType === 'table')
    return <TableOutput columns={result.columns} rows={result.rows} />;
  if (panel.chartType === 'bar')
    return <BarOutput rows={result.rows} xColumn={panel.xColumn} yColumns={panel.yColumns} />;
  if (panel.chartType === 'line')
    return (
      <LineOutput
        rows={result.rows}
        xColumn={panel.xColumn}
        yColumns={panel.yColumns}
        seriesColumn={panel.seriesColumn}
      />
    );
  return null;
}

// ─── Column config — dropdowns if columns known, text input otherwise ─────────
function ColConfig({ panel, result, onChange }) {
  if (panel.chartType === 'table') return null;
  const cols = result?.columns ?? [];
  const ColPicker = ({ label, value, onSet }) =>
    cols.length > 0 ? (
      <Select
        size="small"
        value={value}
        onChange={(e) => onSet(e.target.value)}
        displayEmpty
        sx={{ minWidth: 160 }}
      >
        <MenuItem value="">
          <em>— {label} —</em>
        </MenuItem>
        {cols.map((c) => (
          <MenuItem key={c} value={c}>
            {c}
          </MenuItem>
        ))}
      </Select>
    ) : (
      <TextField
        size="small"
        label={label}
        value={value}
        onChange={(e) => onSet(e.target.value)}
        sx={{ minWidth: 160 }}
      />
    );

  return (
    <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', mt: 1.5 }}>
      <ColPicker label="X Column" value={panel.xColumn} onSet={(v) => onChange({ xColumn: v })} />
      <ColPicker
        label="Y Column"
        value={panel.yColumns[0] ?? ''}
        onSet={(v) => onChange({ yColumns: v ? [v] : [] })}
      />
      {panel.chartType === 'line' && (
        <ColPicker
          label="Series Column (pivot)"
          value={panel.seriesColumn}
          onSet={(v) => onChange({ seriesColumn: v })}
        />
      )}
    </Box>
  );
}

// ─── Single panel card ────────────────────────────────────────────────────────
function PanelCard({ panel, result, onUpdate, onDelete, onRun, dataReady }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Paper elevation={1} sx={{ borderRadius: 2, mb: 2, opacity: panel.enabled ? 1 : 0.5 }}>
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Tooltip title={panel.enabled ? 'Enabled' : 'Disabled'}>
          <Switch
            size="small"
            checked={panel.enabled}
            onChange={(e) => onUpdate({ enabled: e.target.checked })}
          />
        </Tooltip>

        <TextField
          variant="standard"
          value={panel.title}
          onChange={(e) => onUpdate({ title: e.target.value })}
          inputProps={{ style: { fontWeight: 600, fontSize: 14 } }}
          sx={{ flex: 1 }}
        />

        <Select
          size="small"
          value={panel.chartType}
          onChange={(e) => onUpdate({ chartType: e.target.value })}
          sx={{ minWidth: 120, fontSize: 13 }}
        >
          <MenuItem value="table">Table</MenuItem>
          <MenuItem value="bar">Bar Chart</MenuItem>
          <MenuItem value="line">Line Chart</MenuItem>
        </Select>

        <Tooltip title={expanded ? 'Hide SQL' : 'Edit SQL'}>
          <IconButton
            size="small"
            onClick={() => setExpanded((x) => !x)}
            sx={{ color: expanded ? '#667eea' : 'text.secondary' }}
          >
            {expanded ? <CollapseIcon fontSize="small" /> : <SqlIcon fontSize="small" />}
          </IconButton>
        </Tooltip>

        <Tooltip title="Run this panel">
          <span>
            <IconButton
              size="small"
              disabled={!dataReady || result?.loading}
              onClick={onRun}
              sx={{ color: '#667eea' }}
            >
              {result?.loading ? <CircularProgress size={16} /> : <RunIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>

        <Tooltip title="Delete panel">
          <IconButton size="small" onClick={onDelete} sx={{ color: 'error.main' }}>
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* SQL editor + column config */}
      <Collapse in={expanded}>
        <Divider />
        <Box sx={{ px: 2, pt: 1.5, pb: 2 }}>
          <Editor
            language="sql"
            value={panel.sql}
            onChange={(v) => onUpdate({ sql: v ?? '' })}
            height="140px"
            options={{
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              fontSize: 12,
              lineNumbers: 'off',
              wordWrap: 'on',
            }}
          />
          <ColConfig panel={panel} result={result} onChange={onUpdate} />
        </Box>
      </Collapse>

      {/* Output */}
      {result && (
        <Box sx={{ px: 2, pb: 2 }}>
          <PanelOutput panel={panel} result={result} />
        </Box>
      )}
    </Paper>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function PerformanceDashboard() {
  const [dateMode, setDateMode] = useState('all');
  const [date, setDate] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Load panels from localStorage, fall back to defaults
  const [panels, setPanels] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || DEFAULT_PANELS;
    } catch {
      return DEFAULT_PANELS;
    }
  });

  const [panelResults, setPanelResults] = useState({}); // { [id]: { columns, rows, error, loading } }
  const [summaryStats, setSummaryStats] = useState(null);
  const [loadStatus, setLoadStatus] = useState('idle'); // idle | loading | ready | error
  const [loadError, setLoadError] = useState('');
  const dataReady = loadStatus === 'ready';

  // Persist panels (config only, not results)
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(panels));
  }, [panels]);

  const updatePanel = useCallback((id, changes) => {
    setPanels((prev) => prev.map((p) => (p.id === id ? { ...p, ...changes } : p)));
  }, []);

  const deletePanel = useCallback((id) => {
    setPanels((prev) => prev.filter((p) => p.id !== id));
    setPanelResults((prev) => {
      const n = { ...prev };
      delete n[id];
      return n;
    });
  }, []);

  const addPanel = useCallback(() => {
    const id = `panel_${Date.now()}`;
    setPanels((prev) => [
      ...prev,
      {
        id,
        title: 'New Panel',
        chartType: 'table',
        sql: 'SELECT * FROM perf_data LIMIT 100',
        xColumn: '',
        yColumns: [],
        seriesColumn: '',
        enabled: true,
      },
    ]);
  }, []);

  const runPanel = useCallback(
    async (panel) => {
      if (!dataReady) return;
      setPanelResults((prev) => ({
        ...prev,
        [panel.id]: { columns: [], rows: [], error: null, loading: true },
      }));
      const result = await runPanelSQL(panel.sql);
      setPanelResults((prev) => ({ ...prev, [panel.id]: { ...result, loading: false } }));
    },
    [dataReady],
  );

  const handleLoadData = useCallback(
    async (runAll = false) => {
      setLoadStatus('loading');
      setLoadError('');
      setSummaryStats(null);
      setPanelResults({});
      try {
        const stats = await loadPerfData(dateMode, date, startDate, endDate);
        setSummaryStats(stats);
        setLoadStatus('ready');
        if (runAll) {
          // Run all enabled panels sequentially to avoid overwhelming DuckDB
          for (const p of panels.filter((p) => p.enabled)) {
            setPanelResults((prev) => ({
              ...prev,
              [p.id]: { columns: [], rows: [], error: null, loading: true },
            }));
            const result = await runPanelSQL(p.sql);
            setPanelResults((prev) => ({
              ...prev,
              [p.id]: { ...result, loading: false },
            }));
          }
        }
      } catch (e) {
        setLoadError(e.message || String(e));
        setLoadStatus('error');
      }
    },
    [dateMode, date, startDate, endDate, panels],
  );

  const stats = summaryStats;
  const errorRate = stats ? (Number(stats.total_errors) / Number(stats.total_calls)) * 100 : 0;

  return (
    <Box sx={{ p: 3, overflowY: 'auto', height: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'baseline', gap: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, color: '#667eea' }}>
          API Performance Dashboard
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Source: <code>logs/category=PERFORMANCE</code>
        </Typography>
      </Box>

      {/* Date filter + load controls */}
      <Paper elevation={1} sx={{ p: 2.5, borderRadius: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 3, flexWrap: 'wrap' }}>
          <FormControl>
            <FormLabel sx={{ mb: 0.5, fontSize: 12 }}>Date Filter</FormLabel>
            <RadioGroup row value={dateMode} onChange={(e) => setDateMode(e.target.value)}>
              <FormControlLabel value="all" control={<Radio size="small" />} label="All" />
              <FormControlLabel value="single" control={<Radio size="small" />} label="Single" />
              <FormControlLabel value="range" control={<Radio size="small" />} label="Range" />
            </RadioGroup>
          </FormControl>

          {dateMode === 'single' && (
            <TextField
              type="date"
              label="Date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{ alignSelf: 'center' }}
            />
          )}
          {dateMode === 'range' && (
            <Box sx={{ display: 'flex', gap: 1, alignSelf: 'center' }}>
              <TextField
                type="date"
                label="Start"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
              />
              <TextField
                type="date"
                label="End"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
              />
            </Box>
          )}

          <Box sx={{ display: 'flex', gap: 1, alignSelf: 'center', ml: 'auto' }}>
            <Tooltip title="Load data only (run panels manually)">
              <Button
                variant="outlined"
                size="small"
                disabled={loadStatus === 'loading'}
                onClick={() => handleLoadData(false)}
                sx={{ borderColor: '#667eea', color: '#667eea' }}
              >
                {loadStatus === 'loading' ? <CircularProgress size={14} sx={{ mr: 0.5 }} /> : null}
                Load Data
              </Button>
            </Tooltip>
            <Tooltip title="Load data and run all enabled panels">
              <Button
                variant="contained"
                size="small"
                disabled={loadStatus === 'loading'}
                startIcon={
                  loadStatus === 'loading' ? (
                    <CircularProgress size={14} color="inherit" />
                  ) : (
                    <BarChartIcon />
                  )
                }
                onClick={() => handleLoadData(true)}
                sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#5a6fd6' } }}
              >
                Load & Run All
              </Button>
            </Tooltip>
          </Box>
        </Box>
      </Paper>

      {/* Error */}
      {loadStatus === 'error' && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>{loadError}</pre>
        </Alert>
      )}

      {/* Summary stats + alerts */}
      {stats && Number(stats.total_calls) > 0 && (
        <Paper elevation={1} sx={{ p: 2.5, borderRadius: 2, mb: 2 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              mb: 1.5,
            }}
          >
            <Typography variant="subtitle2" sx={{ color: '#667eea', fontWeight: 700 }}>
              Summary — {Number(stats.total_calls).toLocaleString()} records ·{' '}
              {Number(stats.total_errors)} errors
            </Typography>
            <Chip
              label={`Error rate: ${errorRate.toFixed(2)}%`}
              size="small"
              color={errorRate > 5 ? 'error' : 'success'}
            />
          </Box>
          <Grid container spacing={1.5}>
            {[
              { label: 'Avg', value: Number(stats.avg_ms), unit: 'ms' },
              { label: 'Median', value: Number(stats.median_ms), unit: 'ms' },
              {
                label: 'P95',
                value: Number(stats.p95_ms),
                unit: 'ms',
                warn: Number(stats.p95_ms) > 5000,
              },
              { label: 'P99', value: Number(stats.p99_ms), unit: 'ms' },
              { label: 'Max', value: Number(stats.max_ms), unit: 'ms' },
            ].map((c) => (
              <Grid item xs={6} sm={4} md={2} key={c.label}>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 1.5,
                    bgcolor: c.warn ? 'rgba(245,158,11,0.1)' : 'rgba(102,126,234,0.06)',
                    textAlign: 'center',
                  }}
                >
                  <Typography variant="caption" color="text.secondary" display="block">
                    {c.label}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 700,
                      color: c.warn ? '#f59e0b' : '#667eea',
                    }}
                  >
                    {c.value.toFixed(1)}
                    <Typography component="span" variant="caption" color="text.disabled">
                      {' '}
                      {c.unit}
                    </Typography>
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
          {errorRate > 5 && (
            <Alert severity="error" sx={{ mt: 1.5 }}>
              High Error Rate: {errorRate.toFixed(2)}% (threshold: 5%)
            </Alert>
          )}
          {Number(stats.p95_ms) > 5000 && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              Slow P95: {Number(stats.p95_ms).toFixed(0)}ms (threshold: 5000ms)
            </Alert>
          )}
          {errorRate === 0 && Number(stats.p95_ms) < 1000 && (
            <Alert severity="success" sx={{ mt: 1 }}>
              Excellent — no errors, P95 under 1s
            </Alert>
          )}
        </Paper>
      )}

      {/* Panel toolbar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 1.5,
        }}
      >
        <Typography variant="subtitle2" color="text.secondary">
          {panels.filter((p) => p.enabled).length} / {panels.length} panels enabled
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Reset all panels to defaults">
            <Button
              size="small"
              startIcon={<ResetIcon />}
              onClick={() => {
                setPanels(DEFAULT_PANELS);
                setPanelResults({});
              }}
              sx={{ color: 'text.secondary' }}
            >
              Reset
            </Button>
          </Tooltip>
          <Button
            size="small"
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={addPanel}
            sx={{ borderColor: '#667eea', color: '#667eea' }}
          >
            Add Panel
          </Button>
        </Box>
      </Box>

      {/* Panels */}
      {panels.map((panel) => (
        <PanelCard
          key={panel.id}
          panel={panel}
          result={panelResults[panel.id]}
          onUpdate={(changes) => updatePanel(panel.id, changes)}
          onDelete={() => deletePanel(panel.id)}
          onRun={() => runPanel(panel)}
          dataReady={dataReady}
        />
      ))}
    </Box>
  );
}
