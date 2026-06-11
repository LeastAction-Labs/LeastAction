/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import CloseIcon from '@mui/icons-material/Close';
import { Box, Dialog, DialogContent, DialogTitle, IconButton } from '@mui/material';

import { useCatalog } from '@/contexts/CatalogContext';

import MarkdownRenderer from '../MarkdownRenderer';

export interface MarkdownModalData {
  isOpen: boolean;
  title?: string;
  content?: string;
}

export default function MarkdownModal() {
  const { markdownModalState, setMarkdownModalState } = useCatalog();
  const { isOpen, title, content } = markdownModalState;
  const onClose = () => {
    setMarkdownModalState({ isOpen: false });
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'var(--bg-primary)',
          color: 'var(--text-primary)',
          maxHeight: '90vh',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        {title}
        <IconButton
          onClick={onClose}
          sx={{
            color: 'var(--text-secondary)',
            '&:hover': {
              color: 'var(--text-primary)',
              bgcolor: 'var(--bg-tertiary)',
            },
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent
        sx={{
          p: 0,
          overflow: 'auto',
        }}
      >
        <Box sx={{ minHeight: '400px' }}>
          <MarkdownRenderer content={content} />
        </Box>
      </DialogContent>
    </Dialog>
  );
}
