/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { Alert, Box, Button, Typography } from '@mui/material';

import { QuickSearch } from '@/components/ui';
import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS, OPACITY } from '@/constants';
import { AIMode, useAI } from '@/contexts/AIContext';

export default function AIConfig() {
  const { setMode, setConfig } = useAI();
  const navigate = useNavigate();

  const [selectedActionAi, setSelectedActionAi] = useState<any>(null);
  const [selectedConnection, setSelectedConnection] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const handleActionAiSelect = (item: unknown) => {
    const actionItem = item as Record<string, any>;
    setSelectedActionAi(actionItem);
    setError('');
  };

  const handleConnectionSelect = (item: unknown) => {
    const connectionItem = item as Record<string, any>;
    setSelectedConnection(connectionItem);
    setError('');
  };

  const handleContinue = () => {
    if (!selectedActionAi) {
      setError('Please select an AI Chat item');
      return;
    }
    if (!selectedConnection) {
      setError('Please select a Connection');
      return;
    }

    const aiContent =
      typeof selectedActionAi.content === 'string'
        ? JSON.parse(selectedActionAi.content || '{}')
        : selectedActionAi.content || {};
    const aiChatConnection = aiContent.connection || {};

    const connContent =
      typeof selectedConnection.content === 'string'
        ? JSON.parse(selectedConnection.content || '{}')
        : selectedConnection.content || {};

    const merged = { ...aiChatConnection, ...connContent };

    setConfig({
      aiChatLaui: selectedActionAi._laui || selectedActionAi.laui,
      aiChatName: selectedActionAi.name || 'Unnamed AI Chat',
      aiProvider:
        merged.provider || selectedActionAi.item_type?.replace('chat.', '') || 'anthropic',
      connectionLaui: selectedConnection._laui || selectedConnection.laui,
      connectionName: selectedConnection.name || 'Unnamed Connection',
      includeGuideDoc: false,
      includeInstallGuide: false,
    });

    setMode(AIMode.MANUALEDITOR);
  };

  const onBack = () => {
    setMode(AIMode.ITEMTYPE);
    void navigate({ to: '/ai/create', search: { sessionId: undefined } });
  };

  return (
    <Box
      sx={{
        width: '100%',
        maxWidth: 800,
        margin: '0 auto',
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 'calc(100vh - 48px)',
        justifyContent: 'space-between',
        backgroundColor: 'var(--bg-primary)',
      }}
    >
      <Box>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{
              color: 'var(--text-secondary)',
              mb: 2,
              fontSize: FONT_SIZES.SM,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              p: 0,
              minHeight: 'auto',
              textTransform: 'none',
              '&:hover': {
                backgroundColor: 'transparent',
                color: 'var(--accent)',
              },
            }}
          >
            Back
          </Button>

          <Typography
            sx={{
              color: 'var(--text-primary)',
              fontWeight: FONT_WEIGHTS.BOLD,
              fontSize: FONT_SIZES.SM,
              mb: 0.5,
            }}
          >
            Select AI Generate
          </Typography>
        </Box>

        {/* Error Alert */}
        {error && (
          <Alert
            severity="error"
            sx={{
              mb: 1,
              backgroundColor: 'rgba(244, 67, 54, 0.1)',
              color: 'var(--text-primary)',
              border: '1px solid rgba(244, 67, 54, 0.3)',
              fontSize: FONT_SIZES.XS,
              '& .MuiAlert-icon': {
                color: '#f44336',
                fontSize: FONT_SIZES.ICON_MD,
              },
            }}
            onClose={() => setError('')}
          >
            {error}
          </Alert>
        )}

        {/* Action AI QuickSearch */}
        <Box sx={{ mb: 2 }}>
          <QuickSearch
            label="Search AI Generate items"
            placeholder="Search for an AI Chat item..."
            filters={{ item_type: 'generate' }}
            onSelect={handleActionAiSelect}
            value={selectedActionAi?._laui || selectedActionAi?.laui || null}
          />
        </Box>

        {/* Selected Action AI Details */}
        {selectedActionAi && (
          <Box
            sx={{
              p: 2,
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: BORDER_RADIUS.MD,
              mb: 2,
            }}
          >
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-secondary)',
                mb: 0.5,
                fontWeight: FONT_WEIGHTS.WEIGHT_500,
              }}
            >
              Selected AI Chat
            </Typography>
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-primary)',
                fontFamily: 'monospace',
                wordBreak: 'break-all',
                lineHeight: 1.4,
              }}
            >
              Name: {selectedActionAi.name}
              <br />
              LAUI: {selectedActionAi._laui || selectedActionAi.laui}
            </Typography>
          </Box>
        )}

        {/* Connection QuickSearch */}
        <Box sx={{ mb: 2 }}>
          <Typography
            sx={{
              color: 'var(--text-primary)',
              fontWeight: FONT_WEIGHTS.BOLD,
              fontSize: FONT_SIZES.SM,
              mb: 0.5,
            }}
          >
            Select Connection
          </Typography>
          <QuickSearch
            label="Search Connection items"
            placeholder="Search for a Connection..."
            filters={{ item_type: 'connection' }}
            onSelect={handleConnectionSelect}
            value={selectedConnection?._laui || selectedConnection?.laui || null}
          />
        </Box>

        {/* Selected Connection Details */}
        {selectedConnection && (
          <Box
            sx={{
              p: 2,
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              borderRadius: BORDER_RADIUS.MD,
              mb: 2,
            }}
          >
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-secondary)',
                mb: 0.5,
                fontWeight: FONT_WEIGHTS.WEIGHT_500,
              }}
            >
              Selected Connection
            </Typography>
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-primary)',
                fontFamily: 'monospace',
                wordBreak: 'break-all',
                lineHeight: 1.4,
              }}
            >
              Name: {selectedConnection.name}
              <br />
              LAUI: {selectedConnection._laui || selectedConnection.laui}
            </Typography>
          </Box>
        )}

        {/* Action Buttons */}
        <Box
          sx={{
            pt: 1,
            mt: 1,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Button
            variant="outlined"
            onClick={onBack}
            sx={{
              borderColor: 'var(--border)',
              color: 'var(--text-secondary)',
              fontSize: FONT_SIZES.SM,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              px: 4,
              py: 0.75,
              borderRadius: BORDER_RADIUS.MD,
              textTransform: 'none',
              minWidth: 100,
              '&:hover': {
                borderColor: 'var(--accent)',
                backgroundColor: `rgba(var(--color-accent), 0.05)`,
              },
            }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            onClick={handleContinue}
            disabled={!selectedActionAi || !selectedConnection}
            sx={{
              backgroundColor: 'var(--accent)',
              color: 'var(--text-primary)',
              fontSize: FONT_SIZES.SM,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              px: 5,
              py: 0.75,
              borderRadius: BORDER_RADIUS.MD,
              textTransform: 'none',
              minWidth: 100,
              ml: 'auto',
              '&:hover': {
                backgroundColor: 'var(--accent)',
                opacity: OPACITY.HIGH,
              },
              '&.Mui-disabled': {
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-secondary)',
              },
            }}
          >
            Start Session
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
