/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import {
  Add as AddIcon,
  Cancel as CancelIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { Box, Button, IconButton, Tab, Tabs, TextField, Typography } from '@mui/material';

import { BaseModal, MonacoWrapper, TabPanel } from '@/components/ui';
import { FONT_SIZES } from '@/constants';

import type { ArrayItem, FieldConfig } from './types';

const FORMAT_EXT_MAP: Record<string, string> = {
  python: '.py',
  json: '.json',
  bash: '.sh',
  javascript: '.js',
  typescript: '.ts',
};

const getDefaultFileName = (index: number, monacoFormat: string): string => {
  const ext = FORMAT_EXT_MAP[monacoFormat] || '';
  return index === 0 ? `main${ext}` : `file${index + 1}${ext}`;
};

interface ArrayFieldProps {
  field: any;
  arrayValue: ArrayItem[];
  fieldConfig: FieldConfig;
  onChange: (fieldName: string, value: any) => void;
  convertToExternalFormat: (arrayItems: ArrayItem[]) => any;
}

const styles = {
  container: {
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
      fontSize: FONT_SIZES.XS,
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
    minHeight: '32px',
  },
  tabFileName: {
    fontSize: FONT_SIZES.XS,
    color: 'inherit',
  },
  editTabContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 0.5,
    minHeight: '32px',
  },
  editTabInput: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.XS,
      height: '22px',
      '& input': {
        padding: '2px 6px',
        fontSize: FONT_SIZES.XS,
      },
      '& fieldset': {
        borderColor: 'var(--border)',
      },
    },
    width: '120px',
  },
  editIconButton: {
    p: 0,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--primary-main)',
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    '& svg': {
      fontSize: '10px',
    },
  },
  saveIconButton: {
    p: 0,
    color: 'var(--success)',
    '&:hover': {
      color: 'var(--success-dark)',
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
    },
    '& svg': {
      fontSize: '10px',
    },
  },
  cancelIconButton: {
    p: 0,
    color: 'var(--error)',
    '&:hover': {
      color: 'var(--error-dark)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
    '& svg': {
      fontSize: '10px',
    },
  },
  deleteIconButton: {
    p: 0,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--error)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
    '& svg': {
      fontSize: '10px',
    },
  },
  bottomBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mt: 1,
  },
  charCount: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
  },
};

export const ArrayField = ({
  field,
  arrayValue,
  onChange,
  convertToExternalFormat,
}: ArrayFieldProps) => {
  const [arrayTabValue, setArrayTabValue] = useState(0);
  const [editingTabIndex, setEditingTabIndex] = useState<number | null>(null);
  const [editedFileName, setEditedFileName] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    index: number | null;
    fileName: string;
  }>({
    open: false,
    index: null,
    fileName: '',
  });

  const handleArrayTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setArrayTabValue(newValue);
  };

  const handleArrayItemChange = (index: number, newContent: string) => {
    const newArray = [...arrayValue];
    newArray[index] = {
      ...newArray[index],
      content: newContent,
    };
    onChange(field.name, convertToExternalFormat(newArray));
  };

  const addArrayItem = () => {
    const defaultName = getDefaultFileName(arrayValue.length, field.editorMonacoFormat || '');
    const newItem: ArrayItem = {
      fileName: defaultName,
      content: '',
    };
    const newArray = [...arrayValue, newItem];
    const newIndex = newArray.length - 1;
    onChange(field.name, convertToExternalFormat(newArray));
    setArrayTabValue(newIndex);
    // Auto-open the new tab in edit mode
    setEditingTabIndex(newIndex);
    setEditedFileName(defaultName);
  };

  const startEditingTab = (index: number) => {
    setEditingTabIndex(index);
    setEditedFileName(arrayValue[index].fileName);
  };

  const saveEditedTabName = (index: number) => {
    if (editedFileName.trim() && editingTabIndex !== null) {
      const newArray = [...arrayValue];
      newArray[index] = {
        ...newArray[index],
        fileName: editedFileName.trim(),
      };
      onChange(field.name, convertToExternalFormat(newArray));
    }
    setEditingTabIndex(null);
    setEditedFileName('');
  };

  const cancelEditingTab = () => {
    setEditingTabIndex(null);
    setEditedFileName('');
  };

  const requestRemoveTab = (index: number) => {
    setConfirmDialog({
      open: true,
      index,
      fileName: arrayValue[index].fileName,
    });
  };

  const confirmRemoveTab = () => {
    if (confirmDialog.index !== null) {
      const newArray = arrayValue.filter((_: any, i: number) => i !== confirmDialog.index);
      onChange(field.name, convertToExternalFormat(newArray));
      if (arrayTabValue >= newArray.length) {
        setArrayTabValue(Math.max(0, newArray.length - 1));
      }
    }
    setConfirmDialog({ open: false, index: null, fileName: '' });
  };

  const cancelRemoveTab = () => {
    setConfirmDialog({ open: false, index: null, fileName: '' });
  };

  return (
    <Box sx={styles.container}>
      <ConfirmDialog
        open={confirmDialog.open}
        title="Confirm Removal"
        message={`Are you sure you want to remove "${confirmDialog.fileName}"? This action cannot be undone.`}
        onConfirm={confirmRemoveTab}
        onCancel={cancelRemoveTab}
        confirmText="Remove"
      />

      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <IconButton
          onClick={addArrayItem}
          color="primary"
          size="small"
          title={`Add new ${field.name}`}
          sx={{
            bgcolor: 'var(--text-primary)',
            color: 'var(--bg-secondary)',
            fontWeight: 'bold',
            minWidth: '28px',
            minHeight: '28px',
            mr: arrayValue.length > 0 ? 0.5 : 0,
            '&:hover': {
              bgcolor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
            },
            '& svg': {
              fontSize: '14px',
            },
          }}
        >
          <AddIcon />
        </IconButton>
        {arrayValue.length > 0 ? (
          <Tabs
            value={arrayTabValue}
            onChange={handleArrayTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ ...styles.arrayTabs, flex: 1 }}
          >
            {arrayValue.map((item: ArrayItem, index: number) => (
              <Tab
                key={index}
                label={
                  <Box sx={styles.tabLabelContainer}>
                    {editingTabIndex === index ? (
                      <Box sx={styles.editTabContainer}>
                        <TextField
                          value={editedFileName}
                          onChange={(e) => setEditedFileName(e.target.value)}
                          size="small"
                          sx={styles.editTabInput}
                          autoFocus
                          onKeyPress={(e) => {
                            if (e.key === 'Enter') {
                              saveEditedTabName(index);
                            }
                          }}
                        />
                        <IconButton
                          onClick={() => saveEditedTabName(index)}
                          size="small"
                          title="Save"
                          sx={styles.saveIconButton}
                        >
                          <SaveIcon />
                        </IconButton>
                        <IconButton
                          onClick={cancelEditingTab}
                          size="small"
                          title="Cancel"
                          sx={styles.cancelIconButton}
                        >
                          <CancelIcon />
                        </IconButton>
                      </Box>
                    ) : (
                      <>
                        <Typography component="span" sx={styles.tabFileName}>
                          {item.fileName}
                        </Typography>
                        <IconButton
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditingTab(index);
                          }}
                          size="small"
                          title="Edit file name"
                          sx={styles.editIconButton}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          onClick={(e) => {
                            e.stopPropagation();
                            requestRemoveTab(index);
                          }}
                          size="small"
                          title="Remove file"
                          sx={styles.deleteIconButton}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </>
                    )}
                  </Box>
                }
                sx={{
                  fontSize: `${FONT_SIZES.XS} !important`,
                  minHeight: '32px',
                  padding: '0 4px',
                }}
              />
            ))}
          </Tabs>
        ) : null}
      </Box>

      {arrayValue.length > 0 && (
        <Box sx={styles.arrayTabsContainer}>
          {arrayValue.map((item: ArrayItem, index: number) => {
            return (
              <TabPanel key={index} value={arrayTabValue} index={index}>
                <MonacoWrapper
                  content={item.content}
                  fileName={item.fileName}
                  readOnly={false}
                  field={field}
                  onChange={(newContent: string) => handleArrayItemChange(index, newContent)}
                />
                <Box sx={styles.bottomBar}>
                  <Box sx={styles.charCount}>
                    {field.max_length &&
                      `${(item.content || '').length}/${field.max_length} characters`}
                  </Box>
                  <IconButton
                    onClick={() => requestRemoveTab(index)}
                    color="error"
                    size="small"
                    title={`Remove ${item.fileName}`}
                    sx={{
                      color: 'var(--error)',
                      '&:hover': {
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                      },
                      '& svg': {
                        fontSize: '14px',
                      },
                    }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </TabPanel>
            );
          })}
        </Box>
      )}
    </Box>
  );
};

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
}

export function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
}: ConfirmDialogProps) {
  const ModalActions = (
    <>
      <Button
        onClick={onCancel}
        size="small"
        variant="outlined"
        sx={{
          color: 'var(--text-secondary)',
          borderColor: 'var(--border)',
          '&:hover': {
            borderColor: 'var(--primary-main)',
            color: 'var(--text-primary)',
          },
        }}
      >
        {cancelText}
      </Button>
      <Button
        onClick={onConfirm}
        variant="contained"
        sx={{
          bgcolor: 'var(--text-primary)',
          color: 'var(--bg-secondary)',
          textTransform: 'none' as const,
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          },
          py: -1.5,
          px: 0.5,
        }}
      >
        {confirmText}
      </Button>
    </>
  );
  return (
    <BaseModal open={open} onClose={onCancel} title={title} actions={ModalActions}>
      <Typography sx={{ fontSize: '13px', color: 'var(--text-primary)' }}>{message}</Typography>
    </BaseModal>
  );
}
