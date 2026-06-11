/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useEffect, useState } from 'react';

import {
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  Cancel as CancelIcon,
  Code as CodeIcon,
  Delete as DeleteIcon,
  Description as DescriptionIcon,
  Edit as EditIcon,
  EditNote as EditNoteIcon,
  PlayArrow as PlayArrowIcon,
  Save as SaveIcon,
  Settings as SettingsIcon,
  Terminal as TerminalIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';

import RunActionModal from '@/components/modals/RunActionModal';
import { MonacoWrapper } from '@/components/ui';
import {
  BORDER_RADIUS,
  FONT_FAMILIES,
  FONT_SIZES,
  FONT_WEIGHTS,
  LETTER_SPACING,
  LINE_HEIGHTS,
  OPACITY,
} from '@/constants';
import { AIMode, useAI } from '@/contexts/AIContext';
import { RunActionModalMode, useActionContext } from '@/contexts/ActionContext';
import { useNotification } from '@/contexts/NotificationContext';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';

import RunTaskModal from '../../modals/RunTaskModal';
import SaveItemModal from '../SaveItemModal';

interface FileItem {
  id: string;
  fileName: string;
  content: string;
  language: string;
}

interface TabContent {
  id: string;
  label: string;
  icon: React.ReactNode;
  files: FileItem[];
}

const styles = {
  arrayFieldContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  viewModeText: {
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap',
    lineHeight: LINE_HEIGHTS.NORMAL,
    fontFamily: FONT_FAMILIES.PRIMARY,
    backgroundColor: 'var(--bg-tertiary)',
    p: 2,
    borderRadius: BORDER_RADIUS.MD,
  },
  emptyText: {
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },
  arrayTabsContainer: {
    border: 1,
    borderColor: 'var(--border)',
    borderRadius: BORDER_RADIUS.MD,
  },
  arrayTabs: {
    minHeight: '38px',
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none',
      fontSize: FONT_SIZES.SM,
      fontWeight: FONT_WEIGHTS.NORMAL,
      minHeight: '38px',
      minWidth: 'auto',
      px: 2,
      py: 0.5,
      '&.Mui-selected': {
        color: 'var(--accent)',
        fontWeight: FONT_WEIGHTS.BOLD,
      },
    },
    '& .MuiTabs-indicator': {
      bgcolor: 'var(--accent)',
    },
  },
  monacoContainer: {
    height: '400px',
    border: 1,
    borderColor: 'var(--border)',
    borderRadius: BORDER_RADIUS.MD,
  },
  fileNameInputContainer: {
    display: 'flex',
    gap: 1,
    alignItems: 'center',
    mb: 1,
  },
  fileNameInput: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
    },
    flex: 1,
  },
  textField: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
    },
  },
  readOnlyField: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
    },
  },
  viewModeContainer: {
    backgroundColor: 'var(--bg-tertiary)',
    p: 2,
    borderRadius: BORDER_RADIUS.MD,
    border: '1px solid var(--border)',
  },
  fileTabContainer: {
    border: 1,
    borderColor: 'var(--border)',
    borderRadius: BORDER_RADIUS.MD,
    mb: 2,
  },
  fileHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    p: 1.5,
    borderBottom: 1,
    borderColor: 'var(--border)',
    backgroundColor: 'var(--bg-secondary)',
  },
  tabLabelContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
    minHeight: '28px',
  },
  tabFileName: {
    fontSize: FONT_SIZES.SM,
    color: 'inherit',
  },
  editTabContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 0.5,
    minHeight: '20px',
  },
  editTabInput: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.SM,
      height: '28px',
      '& input': {
        padding: '4px 8px',
        fontSize: FONT_SIZES.SM,
      },
      '& fieldset': {
        borderColor: 'var(--border)',
      },
    },
    width: '120px',
  },
  iconButton: {
    p: 0.5,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--text-primary)',
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    '& svg': {
      fontSize: FONT_SIZES.ICON_SM,
    },
  },
  editIconButton: {
    p: 0.5,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--primary-main)',
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    '& svg': {
      fontSize: FONT_SIZES.ICON_SM,
    },
  },
  saveIconButton: {
    p: 0.5,
    color: 'var(--success)',
    '&:hover': {
      color: 'var(--success-dark)',
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
    },
    '& svg': {
      fontSize: FONT_SIZES.ICON_SM,
    },
  },
  cancelIconButton: {
    p: 0.5,
    color: 'var(--error)',
    '&:hover': {
      color: 'var(--error-dark)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
    '& svg': {
      fontSize: FONT_SIZES.ICON_SM,
    },
  },
  deleteIconButton: {
    p: 0.5,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--error)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
    '& svg': {
      fontSize: FONT_SIZES.ICON_SM,
    },
  },
  container: {
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    overflow: 'hidden',
  },
  header: {
    p: 2.5,
    borderBottom: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)',
    flexShrink: 0,
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    minHeight: 0,
  },
  topTabsContainer: {
    borderBottom: '1px solid var(--border)',
    backgroundColor: 'var(--bg-tertiary)',
    flexShrink: 0,
  },
  fileTabsContainer: {
    backgroundColor: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
    px: 3,
    py: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
    flexShrink: 0,
    overflowX: 'auto',
    overflowY: 'hidden',
    whiteSpace: 'nowrap',
    minHeight: '52px',
    '&::-webkit-scrollbar': {
      display: 'none',
    },
    scrollbarWidth: 'none',
  },
  editorContainer: {
    flex: 1,
    position: 'relative',
    minHeight: 0,
    overflow: 'hidden',
  },
  statusBar: {
    height: '40px',
    backgroundColor: 'var(--bg-secondary)',
    borderTop: '1px solid var(--border)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    px: 3,
    flexShrink: 0,
  },
  footer: {
    p: 2.5,
    borderTop: '1px solid var(--border)',
    backgroundColor: 'var(--bg-secondary)',
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 2.5,
    flexShrink: 0,
  },
  menuItem: {
    color: 'var(--text-primary)',
  },
};

// Default content for different item types
const DEFAULT_CONTENT = {
  action: {
    codeblock: `import MODULE

def run(least_action_task_object, param1, param2, ...):
    return true | false`,
  },
  operator: {
    codeblock: `from src.common.logger.logger import log_info

def initialize(least_action_task_object, least_action_parameters):
    return client

def run(least_action_task_object, least_action_parameters, client):
    return {
        'execution_type': 'async' or 'sync',
        'operation_id': 'unique-operation-identifier'
    }

def check_completion(least_action_task_object, least_action_parameters, client, run_details):
    return {
        'state': 'success' | 'failed' | 'pending',
        'message': 'Human-readable state message',
        'output': {}
    }

def finish(least_action_task_object, client, completion_details, run_details):
    return None`,
  },
  payload: {
    payload: 'Any text / JSON / array',
  },
};

const ManualItem = () => {
  const { showSuccess } = useNotification();
  const { itemType, setSaveItemModalState, setMode } = useAI();

  const [activeTab, setActiveTab] = useState(0);
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [cursorPosition, _setCursorPosition] = useState({ line: 1, column: 1 });
  const [fileMenuAnchor, setFileMenuAnchor] = useState<null | HTMLElement>(null);
  const [editingTabIndex, setEditingTabIndex] = useState<number | null>(null);
  const [editedFileName, setEditedFileName] = useState('');
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<number | null>(null);
  const [newFileNameDialogOpen, setNewFileNameDialogOpen] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [runTestLoading, _setRunTestLoading] = useState(false);

  const [tabs, setTabs] = useState<TabContent[]>([
    { id: 'codeblock', label: 'CODEBLOCK', icon: <CodeIcon fontSize="small" />, files: [] },
    { id: 'bashblock', label: 'BASHBLOCK', icon: <TerminalIcon fontSize="small" />, files: [] },
    {
      id: 'connection',
      label: 'CONNECTION',
      icon: <SettingsIcon fontSize="small" />,
      files: [],
    },
    { id: 'payload', label: 'PAYLOAD', icon: <EditNoteIcon fontSize="small" />, files: [] },
    {
      id: 'install_docs',
      label: 'INSTALL DOCS',
      icon: <DescriptionIcon fontSize="small" />,
      files: [],
    },
    {
      id: 'guide_docs',
      label: 'GUIDE DOCS',
      icon: <DescriptionIcon fontSize="small" />,
      files: [],
    },
  ]);

  const isActionType = itemType?.toLowerCase() === 'action';
  const itemTypeLower = itemType?.toLowerCase() || '';
  const isOperatorOrAction = itemTypeLower === 'operator' || itemTypeLower === 'action';
  const visibleTabs = isOperatorOrAction
    ? tabs.filter((t) => t.id !== 'connection' && t.id !== 'payload')
    : tabs;

  const { runActionModalData, setRunActionModalData } = useActionContext();
  const { setTaskModalState } = useTaskModalContext();

  // Initialize default content based on itemType
  useEffect(() => {
    const defaultContent = DEFAULT_CONTENT[itemTypeLower as keyof typeof DEFAULT_CONTENT];
    if (!defaultContent) return;

    const updatedTabs = [...tabs];

    // Set codeblock default for action and operator
    if (
      (itemTypeLower === 'action' || itemTypeLower === 'operator') &&
      'codeblock' in defaultContent
    ) {
      const codeblockContent = defaultContent.codeblock;
      updatedTabs[0].files = [
        {
          id: 'default-code',
          fileName: 'code.py',
          content: codeblockContent,
          language: 'python',
        },
      ];
    }

    // Set payload default for payload
    if (itemTypeLower === 'payload' && 'payload' in defaultContent) {
      const payloadContent = defaultContent.payload;
      updatedTabs[3].files = [
        {
          id: 'default-payload',
          fileName: 'payload.json',
          content: payloadContent,
          language: 'json',
        },
      ];
    }

    setTabs(updatedTabs);

    // Switch to the relevant tab based on item type
    if (itemTypeLower === 'payload') {
      setActiveTab(3); // Switch to PAYLOAD tab
      setSelectedFileIndex(0);
    } else if (itemTypeLower === 'action' || itemTypeLower === 'operator') {
      setActiveTab(0); // Switch to CODEBLOCK tab
      setSelectedFileIndex(0);
    }
  }, [itemType]);

  const hasGeneratedContent = () => {
    return tabs.some(
      (tab) => tab.files.length > 0 && tab.files.some((file) => file.content.trim() !== ''),
    );
  };

  const handleTabChange = (_event: React.SyntheticEvent, visibleIndex: number) => {
    const fullIndex = tabs.indexOf(visibleTabs[visibleIndex]);
    setActiveTab(fullIndex);
    setSelectedFileIndex(0);
  };

  const handleFileSelect = (index: number) => {
    setSelectedFileIndex(index);
  };

  const getDefaultFileName = (tabIndex: number): string => {
    const existingFiles = tabs[tabIndex].files.map((f) => f.fileName);
    let index = 1;
    let baseName = '';

    switch (tabIndex) {
      case 0:
        baseName = 'code';
        break;
      case 1:
        baseName = 'script';
        break;
      case 2:
        return 'connection.json';
      case 3:
        return 'payload.json';
      case 4:
        baseName = 'INSTALL';
        break;
      case 5:
        baseName = 'GUIDE';
        break;
      default:
        baseName = 'file';
    }

    let fileName =
      tabIndex === 2 || tabIndex === 3
        ? baseName
        : `${baseName}.${index}.${getDefaultExtension(tabIndex)}`;

    while (existingFiles.includes(fileName)) {
      index++;
      fileName =
        tabIndex === 2 || tabIndex === 3
          ? baseName
          : `${baseName}.${index}.${getDefaultExtension(tabIndex)}`;
    }

    return fileName;
  };

  const getDefaultExtension = (tabIndex: number): string => {
    switch (tabIndex) {
      case 0:
        return 'py';
      case 1:
        return 'sh';
      case 2:
        return 'json';
      case 3:
        return 'json';
      case 4:
        return 'md';
      case 5:
        return 'md';
      default:
        return 'txt';
    }
  };

  const getLanguageForFile = (fileName: string): string => {
    const ext = fileName.toLowerCase().split('.').pop();
    switch (ext) {
      case 'py':
        return 'python';
      case 'js':
        return 'javascript';
      case 'ts':
        return 'typescript';
      case 'jsx':
        return 'javascript';
      case 'tsx':
        return 'typescript';
      case 'json':
        return 'json';
      case 'sh':
      case 'bash':
        return 'shell';
      case 'md':
        return 'markdown';
      case 'yml':
      case 'yaml':
        return 'yaml';
      case 'html':
        return 'html';
      case 'htm':
        return 'html';
      case 'css':
        return 'css';
      case 'xml':
        return 'xml';
      case 'sql':
        return 'sql';
      case 'java':
        return 'java';
      case 'cpp':
      case 'cc':
      case 'c++':
        return 'cpp';
      case 'c':
        return 'c';
      case 'cs':
        return 'csharp';
      case 'php':
        return 'php';
      case 'rb':
        return 'ruby';
      case 'go':
        return 'go';
      case 'rs':
        return 'rust';
      default:
        return 'plaintext';
    }
  };

  const handleAddFile = () => {
    setNewFileNameDialogOpen(true);
  };

  const handleConfirmAddFile = () => {
    if (!newFileName.trim()) {
      const fileName = getDefaultFileName(activeTab);
      const language = getLanguageForFile(fileName);

      const newFile: FileItem = {
        id: Date.now().toString(),
        fileName: fileName,
        content: '',
        language: language,
      };

      const updatedTabs = [...tabs];
      updatedTabs[activeTab].files.push(newFile);
      setTabs(updatedTabs);
      setSelectedFileIndex(updatedTabs[activeTab].files.length - 1);
    } else {
      const language = getLanguageForFile(newFileName.trim());

      const newFile: FileItem = {
        id: Date.now().toString(),
        fileName: newFileName.trim(),
        content: '',
        language: language,
      };

      const updatedTabs = [...tabs];
      updatedTabs[activeTab].files.push(newFile);
      setTabs(updatedTabs);
      setSelectedFileIndex(updatedTabs[activeTab].files.length - 1);
    }

    setNewFileName('');
    setNewFileNameDialogOpen(false);
  };

  const handleFileContentChange = (value: string | undefined) => {
    const updatedTabs = [...tabs];
    updatedTabs[activeTab].files[selectedFileIndex].content = value || '';
    setTabs(updatedTabs);
  };

  const handleFileMenuClose = () => {
    setFileMenuAnchor(null);
  };

  const startEditingTab = (index: number) => {
    setEditingTabIndex(index);
    setEditedFileName(tabs[activeTab].files[index].fileName);
  };

  const saveEditedTabName = (index: number) => {
    if (editedFileName.trim() && editingTabIndex !== null) {
      const updatedTabs = [...tabs];
      updatedTabs[activeTab].files[index] = {
        ...updatedTabs[activeTab].files[index],
        fileName: editedFileName.trim(),
        language: getLanguageForFile(editedFileName.trim()),
      };
      setTabs(updatedTabs);
    }
    setEditingTabIndex(null);
    setEditedFileName('');
  };

  const cancelEditingTab = () => {
    setEditingTabIndex(null);
    setEditedFileName('');
  };

  const requestDeleteFile = (index: number) => {
    setFileToDelete(index);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteFile = () => {
    if (fileToDelete !== null) {
      const updatedTabs = [...tabs];
      updatedTabs[activeTab].files.splice(fileToDelete, 1);
      setTabs(updatedTabs);

      if (
        selectedFileIndex >= updatedTabs[activeTab].files.length &&
        updatedTabs[activeTab].files.length > 0
      ) {
        setSelectedFileIndex(updatedTabs[activeTab].files.length - 1);
      } else if (updatedTabs[activeTab].files.length === 0) {
        setSelectedFileIndex(0);
      }
    }
    setFileToDelete(null);
    setDeleteConfirmOpen(false);
  };

  const handleSaveClick = () => {
    setSaveItemModalState({
      isOpen: true,
      itemData: {
        codeblock: tabs[0].files.reduce(
          (acc, file) => ({
            ...acc,
            [file.fileName]: file.content,
          }),
          {},
        ),
        bashblock: tabs[1].files.reduce(
          (acc, file) => ({
            ...acc,
            [file.fileName]: file.content,
          }),
          {},
        ),
        connection: tabs[2].files.length > 0 ? JSON.parse(tabs[2].files[0].content) : {},
        payload: tabs[3].files.length > 0 ? JSON.parse(tabs[3].files[0].content) : {},
        install_guide: tabs[4].files.reduce(
          (acc, file) => ({
            ...acc,
            [file.fileName]: file.content,
          }),
          {},
        ),
        guide: tabs[5].files.reduce(
          (acc, file) => ({
            ...acc,
            [file.fileName]: file.content,
          }),
          {},
        ),
      },
    });
  };

  const handleRunTestClick = () => {
    if (!hasGeneratedContent()) {
      showSuccess('Please add content to at least one file before running test.');
      return;
    }
    const operatorData = {
      prompt: '',
      install_docs: tabs[4].files.reduce(
        (acc, file) => ({
          ...acc,
          [file.fileName]: file.content,
        }),
        {},
      ),
      guide_docs: tabs[5].files.reduce(
        (acc, file) => ({
          ...acc,
          [file.fileName]: file.content,
        }),
        {},
      ),
      codeblock: tabs[0].files.reduce(
        (acc, file) => ({
          ...acc,
          [file.fileName]: file.content,
        }),
        {},
      ),
      bashblock: tabs[1].files.reduce(
        (acc, file) => ({
          ...acc,
          [file.fileName]: file.content,
        }),
        {},
      ),
    };

    if (isActionType) {
      setRunActionModalData({
        isOpen: true,
        mode: RunActionModalMode.CREATE,
        actionVariables: tabs[3].files.length > 0 ? JSON.parse(tabs[3].files[0].content) : {},
        operatorData,
      });
      return;
    }
    setTaskModalState({
      isOpen: true,
      mode: TaskModalMode.RUN,
      scope: { scopeType: TaskModalScopeType.AI },
      operatorData,
    });
  };

  const currentTab = tabs[activeTab];
  const currentFile = currentTab.files[selectedFileIndex];

  const onBack = () => {
    setMode(AIMode.ITEMTYPE);
  };

  const onSwitchToAI = () => {
    setMode(AIMode.AICONFIG);
  };

  return (
    <Box sx={styles.container}>
      <Box sx={styles.header}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: 1,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton
              onClick={onBack}
              sx={{
                color: 'var(--text-secondary)',
                '&:hover': {
                  color: 'var(--accent)',
                  backgroundColor: 'rgba(var(--color-accent), 0.1)',
                },
              }}
            >
              <ArrowBackIcon />
            </IconButton>
            <Typography
              sx={{
                color: 'var(--text-primary)',
                fontWeight: FONT_WEIGHTS.BOLD,
                fontSize: FONT_SIZES.MD,
                fontFamily: FONT_FAMILIES.PRIMARY,
              }}
            >
              Create Manual Item
            </Typography>
          </Box>

          <Button
            variant="outlined"
            onClick={onSwitchToAI}
            sx={{
              borderColor: 'var(--border)',
              color: 'var(--text-secondary)',
              fontSize: FONT_SIZES.BASE,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              px: 3,
              py: 1,
              borderRadius: BORDER_RADIUS.MD,
              textTransform: 'none',
              fontFamily: FONT_FAMILIES.PRIMARY,
              letterSpacing: LETTER_SPACING.NORMAL,
              '&:hover': {
                borderColor: 'var(--accent)',
                backgroundColor: `rgba(var(--color-accent), 0.05)`,
              },
            }}
          >
            Switch to AI Generator
          </Button>
        </Box>
      </Box>
      <Box sx={styles.mainContent}>
        <Box sx={styles.topTabsContainer}>
          <Tabs
            value={Math.max(0, visibleTabs.indexOf(tabs[activeTab]))}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={styles.arrayTabs}
          >
            {visibleTabs.map((tab) => (
              <Tab
                key={tab.id}
                // icon={tab.icon}
                iconPosition="start"
                label={tab.label}
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontFamily: FONT_FAMILIES.PRIMARY,
                  minHeight: '38px',
                  px: 2,
                  py: 0.5,
                  letterSpacing: LETTER_SPACING.WIDE,
                  '&.Mui-selected': {
                    color: 'var(--accent)',
                    fontWeight: FONT_WEIGHTS.BOLD,
                  },
                }}
              />
            ))}
          </Tabs>
        </Box>

        {/* File Tabs Header */}
        <Box sx={styles.fileTabsContainer}>
          <Button
            startIcon={<AddIcon />}
            onClick={handleAddFile}
            size="small"
            sx={{
              fontSize: FONT_SIZES.SM,
              fontFamily: FONT_FAMILIES.PRIMARY,
              color: 'var(--text-secondary)',
              textTransform: 'none',
              minWidth: 'auto',
              letterSpacing: LETTER_SPACING.NORMAL,
              '&:hover': {
                color: 'var(--accent)',
                backgroundColor: 'rgba(var(--color-accent), 0.1)',
              },
            }}
          >
            Add File
          </Button>
        </Box>

        {/* File Tabs - Only show tabs, NOT the editor content */}
        {currentTab.files.length > 0 && (
          <Box sx={styles.fileTabContainer}>
            <Box sx={styles.arrayTabsContainer}>
              <Tabs
                value={selectedFileIndex}
                onChange={(_e, newValue) => handleFileSelect(newValue)}
                variant="scrollable"
                scrollButtons="auto"
                sx={styles.arrayTabs}
              >
                {currentTab.files.map((item, index) => (
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
                                requestDeleteFile(index);
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
                      fontSize: FONT_SIZES.SM,
                      fontFamily: FONT_FAMILIES.PRIMARY,
                      minHeight: '34px',
                      padding: '4px 8px',
                    }}
                  />
                ))}
              </Tabs>
            </Box>
          </Box>
        )}

        {/* Editor Area - This is where the actual editor content goes */}
        <Box sx={styles.editorContainer}>
          {currentFile ? (
            <>
              <MonacoWrapper
                content={currentFile.content}
                fileName={currentFile.fileName}
                onChange={handleFileContentChange}
                field={''}
              />
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  mt: 1,
                  px: 1,
                  pb: 1,
                }}
              >
                <Box
                  sx={{
                    fontSize: FONT_SIZES.SM,
                    color: 'var(--text-secondary)',
                    fontFamily: FONT_FAMILIES.PRIMARY,
                  }}
                >
                  {(currentFile.content || '').length} characters
                </Box>
                <IconButton
                  onClick={() => requestDeleteFile(selectedFileIndex)}
                  color="error"
                  size="small"
                  title={`Remove ${currentFile.fileName}`}
                  sx={{
                    color: 'var(--error)',
                    '&:hover': {
                      backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    },
                    '& svg': {
                      fontSize: FONT_SIZES.ICON_SM,
                    },
                  }}
                >
                  <DeleteIcon />
                </IconButton>
              </Box>
            </>
          ) : (
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                color: 'var(--text-secondary)',
                flexDirection: 'column',
                gap: 2,
              }}
            >
              <Typography
                sx={{
                  fontFamily: FONT_FAMILIES.PRIMARY,
                  fontSize: FONT_SIZES.MD,
                }}
              >
                No files created yet.
              </Typography>
              <Button
                startIcon={<AddIcon />}
                onClick={handleAddFile}
                size="small"
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontFamily: FONT_FAMILIES.PRIMARY,
                  color: 'var(--accent)',
                  textTransform: 'none',
                  letterSpacing: LETTER_SPACING.NORMAL,
                  '&:hover': {
                    backgroundColor: 'rgba(var(--color-accent), 0.1)',
                  },
                }}
              >
                Click to add your first file
              </Button>
            </Box>
          )}
        </Box>

        {/* Status Bar */}
        <Box sx={styles.statusBar}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography
              sx={{
                fontSize: FONT_SIZES.SM,
                fontFamily: FONT_FAMILIES.PRIMARY,
                color: 'var(--text-secondary)',
                fontWeight: FONT_WEIGHTS.WEIGHT_500,
                textTransform: 'uppercase',
                letterSpacing: LETTER_SPACING.WIDE,
              }}
            >
              {itemType}
            </Typography>

            <Divider
              orientation="vertical"
              flexItem
              sx={{ height: '16px', backgroundColor: 'var(--border)' }}
            />

            <Typography
              sx={{
                fontSize: FONT_SIZES.SM,
                fontFamily: FONT_FAMILIES.PRIMARY,
                color: 'var(--text-secondary)',
              }}
            >
              {currentFile ? `${currentFile.language.toUpperCase()}` : 'No file selected'}
            </Typography>
          </Box>

          <Typography
            sx={{
              fontSize: FONT_SIZES.SM,
              fontFamily: FONT_FAMILIES.MONOSPACE,
              color: 'var(--text-secondary)',
            }}
          >
            Ln {cursorPosition.line}, Col {cursorPosition.column}
          </Typography>
        </Box>
      </Box>

      {/* Footer */}
      <Box sx={styles.footer}>
        <Button
          variant="outlined"
          startIcon={<PlayArrowIcon />}
          onClick={handleRunTestClick}
          disabled={!hasGeneratedContent() || runTestLoading}
          sx={{
            borderColor: 'var(--border)',
            color: 'var(--text-secondary)',
            fontSize: FONT_SIZES.BASE,
            fontFamily: FONT_FAMILIES.PRIMARY,
            fontWeight: FONT_WEIGHTS.WEIGHT_500,
            px: 4,
            py: 1,
            borderRadius: BORDER_RADIUS.MD,
            textTransform: 'none',
            minWidth: 130,
            letterSpacing: LETTER_SPACING.NORMAL,
            '&:hover': {
              borderColor: 'var(--accent)',
              backgroundColor: `rgba(var(--color-accent), 0.05)`,
            },
            '&.Mui-disabled': {
              color: 'var(--text-disabled)',
              borderColor: 'var(--border)',
            },
          }}
        >
          {runTestLoading ? 'Running...' : 'Run Test'}
        </Button>

        <Button
          variant="contained"
          startIcon={<SaveIcon />}
          onClick={handleSaveClick}
          sx={{
            backgroundColor: 'var(--accent)',
            color: 'var(--text-primary)',
            fontSize: FONT_SIZES.BASE,
            fontFamily: FONT_FAMILIES.PRIMARY,
            fontWeight: FONT_WEIGHTS.WEIGHT_500,
            px: 4,
            py: 1,
            borderRadius: BORDER_RADIUS.MD,
            textTransform: 'none',
            minWidth: 120,
            letterSpacing: LETTER_SPACING.NORMAL,
            '&:hover': {
              backgroundColor: 'var(--accent)',
              opacity: OPACITY.HIGH,
            },
          }}
        >
          Save Item
        </Button>
      </Box>

      <Menu
        anchorEl={fileMenuAnchor}
        open={Boolean(fileMenuAnchor)}
        onClose={handleFileMenuClose}
        PaperProps={{
          sx: {
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: BORDER_RADIUS.MD,
          },
        }}
      >
        <MenuItem onClick={handleAddFile} sx={styles.menuItem}>
          <AddIcon fontSize="small" sx={{ mr: 1, fontSize: FONT_SIZES.ICON_SM }} />
          Add New File
        </MenuItem>
      </Menu>

      {/* New File Name Dialog */}
      <Dialog
        open={newFileNameDialogOpen}
        onClose={() => setNewFileNameDialogOpen(false)}
        PaperProps={{
          sx: {
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: BORDER_RADIUS.MD,
          },
        }}
      >
        <DialogTitle
          sx={{
            color: 'var(--text-primary)',
            fontFamily: FONT_FAMILIES.PRIMARY,
            fontSize: FONT_SIZES.MD,
          }}
        >
          Add New File
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="File Name"
            type="text"
            fullWidth
            value={newFileName}
            onChange={(e) => setNewFileName(e.target.value)}
            placeholder="Leave empty for default name"
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                fontFamily: FONT_FAMILIES.PRIMARY,
                fontSize: FONT_SIZES.SM,
              },
              '& .MuiInputLabel-root': {
                color: 'var(--text-secondary)',
                fontFamily: FONT_FAMILIES.PRIMARY,
                fontSize: FONT_SIZES.SM,
              },
            }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleConfirmAddFile();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setNewFileNameDialogOpen(false)}
            sx={{
              color: 'var(--text-secondary)',
              fontFamily: FONT_FAMILIES.PRIMARY,
              fontSize: FONT_SIZES.SM,
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirmAddFile}
            sx={{
              color: 'var(--accent)',
              fontFamily: FONT_FAMILIES.PRIMARY,
              fontSize: FONT_SIZES.SM,
            }}
          >
            Add File
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        PaperProps={{
          sx: {
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: BORDER_RADIUS.MD,
          },
        }}
      >
        <DialogTitle
          sx={{
            color: 'var(--text-primary)',
            fontFamily: FONT_FAMILIES.PRIMARY,
            fontSize: FONT_SIZES.MD,
          }}
        >
          Confirm Delete
        </DialogTitle>
        <DialogContent
          sx={{
            color: 'var(--text-secondary)',
            fontFamily: FONT_FAMILIES.PRIMARY,
            fontSize: FONT_SIZES.SM,
          }}
        >
          Are you sure you want to delete{' '}
          {fileToDelete !== null ? currentTab.files[fileToDelete]?.fileName : 'this file'}?
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteConfirmOpen(false)}
            sx={{
              color: 'var(--text-secondary)',
              fontFamily: FONT_FAMILIES.PRIMARY,
              fontSize: FONT_SIZES.SM,
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleDeleteFile}
            sx={{
              color: 'var(--error)',
              fontFamily: FONT_FAMILIES.PRIMARY,
              fontSize: FONT_SIZES.SM,
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modals */}
      <SaveItemModal />

      {isActionType ? (
        <RunActionModal open={runActionModalData?.isOpen || false} />
      ) : (
        <RunTaskModal />
      )}
    </Box>
  );
};

export default ManualItem;
