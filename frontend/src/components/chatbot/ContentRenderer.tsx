/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import CloseIcon from '@mui/icons-material/Close';
import OpenInFullIcon from '@mui/icons-material/OpenInFull';
import { Box, Dialog, DialogContent, IconButton, Tooltip, Typography } from '@mui/material';

import MarkdownRenderer from '@/components/browse/MarkdownRenderer';
import IframeContent from '@/components/ui/IframeContent';
import { MonacoWrapper } from '@/components/ui/MonacoWrapper';
import { FONT_SIZES } from '@/constants';

interface ContentRendererProps {
  content: string;
  contentType?: string;
  showExpand?: boolean;
}

function ExpandButton({ onClick }: { onClick: () => void }) {
  return (
    <Tooltip title="Expand" placement="top">
      <IconButton
        size="small"
        onClick={onClick}
        sx={{
          position: 'absolute',
          top: 6,
          right: 6,
          bgcolor: 'rgba(0,0,0,0.45)',
          color: '#fff',
          p: 0.4,
          zIndex: 2,
          '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' },
        }}
      >
        <OpenInFullIcon sx={{ fontSize: 14 }} />
      </IconButton>
    </Tooltip>
  );
}

function FullscreenDialog({
  open,
  onClose,
  content,
  contentType,
}: {
  open: boolean;
  onClose: () => void;
  content: string;
  contentType: string;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={false}
      fullWidth
      slotProps={{
        paper: {
          sx: {
            width: '96vw',
            height: '96vh',
            maxWidth: '96vw',
            maxHeight: '96vh',
            bgcolor: 'var(--bg-primary)',
            display: 'flex',
            flexDirection: 'column',
          },
        },
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          px: 1.5,
          py: 1,
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
        }}
      >
        <IconButton size="small" onClick={onClose} sx={{ color: 'var(--text-secondary)' }}>
          <CloseIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </Box>
      <DialogContent
        sx={{ p: 0, flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
      >
        {contentType === 'html' && <IframeContent content={content} height="100%" />}
        {contentType === 'markdown' && (
          <Box sx={{ overflow: 'auto', flex: 1 }}>
            <MarkdownRenderer content={content} containerSx={{ maxWidth: '100%', mx: 0 }} />
          </Box>
        )}
        {(contentType === 'sql' || contentType === 'code') && (
          <MonacoWrapper content={content} field={{ fontSize: 14 }} readOnly height="100%" />
        )}
        {contentType === 'text' && (
          <Box sx={{ p: 3, overflow: 'auto', flex: 1 }}>
            <Typography
              sx={{
                fontSize: FONT_SIZES.SM,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.7,
                color: 'var(--text-primary)',
              }}
            >
              {content}
            </Typography>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

const MARKDOWN_EXPAND_THRESHOLD = 600;

export default function ContentRenderer({
  content,
  contentType = 'markdown',
  showExpand = true,
}: ContentRendererProps) {
  const [expanded, setExpanded] = useState(false);

  const canExpand =
    showExpand && (contentType !== 'markdown' || content.length > MARKDOWN_EXPAND_THRESHOLD);
  const expandButton = canExpand ? <ExpandButton onClick={() => setExpanded(true)} /> : null;
  const dialog = (
    <FullscreenDialog
      open={expanded}
      onClose={() => setExpanded(false)}
      content={content}
      contentType={contentType}
    />
  );

  switch (contentType) {
    case 'html':
      return (
        <>
          <Box
            sx={{
              position: 'relative',
              width: '100%',
              borderRadius: 1,
              overflow: 'hidden',
              border: '1px solid var(--border)',
            }}
          >
            {expandButton}
            <IframeContent content={content} />
          </Box>
          {dialog}
        </>
      );

    case 'markdown':
      return (
        <>
          <Box sx={{ position: 'relative' }}>
            {expandButton}
            <MarkdownRenderer content={content} containerSx={{ maxWidth: '100%', mx: 0, p: 1 }} />
          </Box>
          {dialog}
        </>
      );

    case 'sql':
    case 'code':
      return (
        <>
          <Box sx={{ position: 'relative' }}>
            {expandButton}
            <MonacoWrapper content={content} field={{ fontSize: 12 }} readOnly maxHeight={400} />
          </Box>
          {dialog}
        </>
      );

    default:
      return (
        <>
          <Box sx={{ position: 'relative' }}>
            {expandButton}
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                whiteSpace: 'pre-wrap',
                lineHeight: 1.5,
                pr: 3,
              }}
            >
              {content}
            </Typography>
          </Box>
          {dialog}
        </>
      );
  }
}
