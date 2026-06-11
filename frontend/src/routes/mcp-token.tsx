/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { createFileRoute } from '@tanstack/react-router';

import { Check, ContentCopy, Terminal } from '@mui/icons-material';
import {
  Alert,
  Box,
  Container,
  Divider,
  IconButton,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material';

import { CORE_BACKEND_URL } from '@/config/urls';

export const Route = createFileRoute('/mcp-token')({
  component: McpTokenPage,
});

function CopyableBlock({ content, label }: { content: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Box sx={{ position: 'relative' }}>
      <Typography
        variant="caption"
        sx={{
          color: 'var(--text-secondary)',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          fontWeight: 600,
          display: 'block',
          mb: 0.5,
        }}
      >
        {label}
      </Typography>
      <Box
        sx={{
          bgcolor: 'var(--bg-primary)',
          border: '1px solid var(--border)',
          borderRadius: 1,
          p: 1.5,
          fontFamily: 'monospace',
          fontSize: '0.78rem',
          whiteSpace: 'pre',
          overflowX: 'auto',
          color: 'var(--text-primary)',
          position: 'relative',
          pr: 5,
        }}
      >
        {content}
        <Tooltip title={copied ? 'Copied!' : 'Copy'}>
          <IconButton
            size="small"
            onClick={handleCopy}
            sx={{
              position: 'absolute',
              top: 6,
              right: 6,
              color: 'var(--text-secondary)',
              '&:hover': { color: 'var(--text-primary)' },
            }}
          >
            {copied ? <Check fontSize="small" /> : <ContentCopy fontSize="small" />}
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
}

function McpTokenPage() {
  const [token, setToken] = useState('');
  // .mcp.json is consumed by external tools (Claude Code), so the URL must be
  // absolute. CORE_BACKEND_URL is "" in same-origin deployments — fall back to
  // the origin the app is being served from.
  const mcpUrl = `${CORE_BACKEND_URL || window.location.origin}/mcp/`;

  useEffect(() => {
    fetch(`${CORE_BACKEND_URL}/api/v1/get-mcp-token`, { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setToken(d.access_token ?? ''))
      .catch(() => {});
  }, []);

  const mcpJson = JSON.stringify(
    {
      mcpServers: {
        leastaction: {
          type: 'http',
          url: mcpUrl,
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    },
    null,
    2,
  );

  return (
    <Container component="main" maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            width: '100%',
            maxWidth: 600,
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
            <Terminal sx={{ fontSize: 28, color: 'var(--text-secondary)' }} />
            <Typography variant="h5" fontWeight="bold">
              Claude Code MCP
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ color: 'var(--text-secondary)', mb: 3 }}>
            Connect Claude Code to this LeastAction instance. Copy the snippet below into your{' '}
            <code style={{ fontFamily: 'monospace' }}>.mcp.json</code> at the project root, then
            restart Claude Code.
          </Typography>

          <Divider sx={{ borderColor: 'var(--border)', mb: 3 }} />

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <CopyableBlock content={mcpJson} label=".mcp.json snippet" />

            <Alert
              severity="info"
              sx={{
                bgcolor: 'var(--bg-primary)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                '& .MuiAlert-icon': { color: 'var(--text-secondary)' },
              }}
            >
              This token expires in 24 hours. Return to this page to get a fresh one after
              re-logging in.
            </Alert>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
