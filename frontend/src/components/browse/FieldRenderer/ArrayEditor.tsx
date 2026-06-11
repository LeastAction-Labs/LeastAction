/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import {
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { Box, IconButton, Tab, Tabs, TextField, Typography } from '@mui/material';

import { MonacoWrapper, TabPanel } from '@/components/ui';

import type { ArrayItem } from './types';

const styles = {
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
  tabLabelContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 0.5,
  },
  tabFileName: {
    fontSize: '12px',
  },
  editTabInput: {
    '& .MuiOutlinedInput-root': {
      height: '22px',
      fontSize: '12px',
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
    },
    width: '120px',
  },
  saveIconButton: {
    p: 0,
    color: 'var(--success)',
    '& svg': { fontSize: '12px' },
  },
  cancelIconButton: {
    p: 0,
    color: 'var(--error)',
    '&:hover': {
      color: 'var(--error-dark)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
    '& svg': { fontSize: '12px' },
  },
  editIconButton: {
    p: 0,
    '& svg': { fontSize: '12px' },
  },
  deleteIconButton: {
    p: 0,
    '&:hover': { color: 'var(--error)' },
    '& svg': { fontSize: '12px' },
  },
};

interface ArrayEditorProps {
  items: ArrayItem[];
  field: any;
  onUpdate: (items: ArrayItem[]) => void;
  onDelete: (index: number) => void;
}

export const ArrayEditor = ({ items, field, onUpdate, onDelete }: ArrayEditorProps) => {
  const [tabIndex, setTabIndex] = useState(0);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [tempFileName, setTempFileName] = useState('');

  const handleRename = (index: number) => {
    if (tempFileName.trim()) {
      const newItems = [...items];
      newItems[index].fileName = tempFileName.trim();
      onUpdate(newItems);
    }
    setEditingIndex(null);
    setTempFileName('');
  };

  const cancelRename = () => {
    setEditingIndex(null);
    setTempFileName('');
  };

  const handleContentChange = (index: number, content: string) => {
    const newItems = [...items];
    newItems[index].content = content;
    onUpdate(newItems);
  };

  return (
    <Box sx={styles.arrayTabsContainer}>
      <Tabs
        value={tabIndex}
        onChange={(_, v) => setTabIndex(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={styles.arrayTabs}
      >
        {items.map((item, i) => (
          <Tab
            key={i}
            label={
              <Box sx={styles.tabLabelContainer}>
                {editingIndex === i ? (
                  <>
                    <TextField
                      value={tempFileName}
                      autoFocus
                      size="small"
                      sx={styles.editTabInput}
                      onChange={(e) => setTempFileName(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleRename(i);
                        } else if (e.key === 'Escape') {
                          cancelRename();
                        }
                      }}
                    />
                    <IconButton onClick={() => handleRename(i)} sx={styles.saveIconButton}>
                      <SaveIcon />
                    </IconButton>
                    <IconButton onClick={cancelRename} sx={styles.cancelIconButton}>
                      <CancelIcon />
                    </IconButton>
                  </>
                ) : (
                  <>
                    <Typography sx={styles.tabFileName}>{item.fileName}</Typography>
                    <IconButton
                      onClick={() => {
                        setEditingIndex(i);
                        setTempFileName(item.fileName);
                      }}
                      sx={styles.editIconButton}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton onClick={() => onDelete(i)} sx={styles.deleteIconButton}>
                      <DeleteIcon />
                    </IconButton>
                  </>
                )}
              </Box>
            }
          />
        ))}
      </Tabs>
      {items.map((item, i) => (
        <TabPanel key={i} value={tabIndex} index={i}>
          <MonacoWrapper
            content={item.content}
            fileName={item.fileName}
            field={field}
            onChange={(v: string) => handleContentChange(i, v)}
          />
        </TabPanel>
      ))}
    </Box>
  );
};
