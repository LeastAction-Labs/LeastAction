/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import ViteYaml from '@modyfi/vite-plugin-yaml';
import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-vite-plugin';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// todo move to API: Fixed logs root — mirrors performance_analysis.py: script_dir/'logs/category=PERFORMANCE'
const PERF_LOGS_DIR = path.resolve(__dirname, '../logs/category=PERFORMANCE');

/** todo move to API: Recursively collect all .log paths relative to PERF_LOGS_DIR */
function collectLogFiles(dir: string, rel = ''): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const relPath = rel ? `${rel}/${e.name}` : e.name;
    if (e.isDirectory()) return collectLogFiles(path.join(dir, e.name), relPath);
    if (e.name.endsWith('.log')) return [relPath];
    return [];
  });
}

/** todo move to API: Vite dev-only plugin: exposes two endpoints for PerformanceDashboard */
function perfLogsPlugin() {
  return {
    name: 'perf-logs',
    configureServer(server: any) {
      // GET /api/perf-logs/list  → JSON array of relative paths (yyyy=N/mm=N/dd=N/file.log)
      server.middlewares.use('/api/perf-logs/list', (_req: any, res: any) => {
        try {
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(collectLogFiles(PERF_LOGS_DIR)));
        } catch (e: any) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: e.message }));
        }
      });
      // GET /api/perf-logs/file?p=yyyy=N/mm=N/dd=N/file.log  → raw file bytes
      server.middlewares.use('/api/perf-logs/file', (req: any, res: any) => {
        const relPath = new URL(req.url, 'http://x').searchParams.get('p') ?? '';
        const full = path.join(PERF_LOGS_DIR, relPath);
        if (!full.startsWith(PERF_LOGS_DIR)) {
          res.statusCode = 403;
          res.end();
          return;
        }
        fs.readFile(full, (err, data) => {
          if (err) {
            res.statusCode = 404;
            res.end();
            return;
          }
          res.end(data);
        });
      });
    },
  };
}

export default defineConfig({
  server: {
    host: true,
    fs: {
      allow: ['..'],
    },
  },
  optimizeDeps: {
    exclude: ['@duckdb/duckdb-wasm'],
  },
  plugins: [
    perfLogsPlugin(),
    tailwindcss(),
    react(),
    ViteYaml(),
    TanStackRouterVite({
      routesDirectory: 'src/routes',
      generatedRouteTree: 'src/routeTree.gen.ts',
    }),
  ],
  resolve: {
    alias: {
      // 2. Define the @ alias
      '@': path.resolve(__dirname, './src'),
    },
  },
});
