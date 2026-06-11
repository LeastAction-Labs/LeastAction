/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useRef, useState } from 'react';

import type { DeleteModalData } from '@/components/browse/modals/DeleteModal';
import type { ImportModalData } from '@/components/browse/modals/ImportModal';
import type { MarkdownModalData } from '@/components/browse/modals/MarkdownModal';
import type { RestoreModalData } from '@/components/browse/modals/RestoreModal';
import type { SaveConfirmModalData } from '@/components/browse/modals/SaveConfirmModal';
import type { ShareModalData } from '@/components/browse/modals/ShareModal';
import type { EditorStateType } from '@/screens/Browse/hooks/useCatalogEditor';
import { useEditorState } from '@/screens/Browse/hooks/useCatalogEditor';

import { useCatalogState } from '../screens/Browse/hooks';
import type { CatalogStateType } from '../screens/Browse/hooks/useCatalogState';

export enum CatalogMode {
  'DEFAULT' = 'default',
  'USERS' = 'users',
  'GROUPS' = 'groups',
}

interface CatalogContextType {
  mode: CatalogMode;
  deleteModalState: DeleteModalData;
  saveConfirmModalState: SaveConfirmModalData;
  shareModalState: ShareModalData;
  restoreModalState: RestoreModalData;
  markdownModalState: MarkdownModalData;
  importModalState: ImportModalData;
  catalogState: CatalogStateType;
  editorState: EditorStateType;
  setMode: (mode: CatalogMode) => void;
  setDeleteModalState: (state: DeleteModalData) => void;
  setSaveConfirmModalState: (state: SaveConfirmModalData) => void;
  setShareModalState: (state: ShareModalData) => void;
  setRestoreModalState: (state: RestoreModalData) => void;
  setMarkdownModalState: (state: MarkdownModalData) => void;
  setImportModalState: (state: ImportModalData) => void;
  markNavigatedInAppRef: React.RefObject<((laui: string) => void) | null>;
}

const CatalogContext = createContext<CatalogContextType | undefined>(undefined);

export const CatalogProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<CatalogMode>(CatalogMode.DEFAULT);
  const [deleteModalState, setDeleteModalState] = useState<DeleteModalData>({
    isOpen: false,
    itemName: '',
  });
  const [saveConfirmModalState, setSaveConfirmModalState] = useState<SaveConfirmModalData>({
    isOpen: false,
  });
  const [shareModalState, setShareModalState] = useState<ShareModalData>({ isOpen: false });
  const [markdownModalState, setMarkdownModalState] = useState<MarkdownModalData>({
    isOpen: false,
  });
  const [restoreModalState, setRestoreModalState] = useState<RestoreModalData>({ isOpen: false });
  const [importModalState, setImportModalState] = useState<ImportModalData>({ isOpen: false });
  const catalogState: CatalogStateType = useCatalogState();
  const editorState: EditorStateType = useEditorState();
  const markNavigatedInAppRef = useRef<((laui: string) => void) | null>(null);

  return (
    <CatalogContext.Provider
      value={{
        mode,
        deleteModalState,
        saveConfirmModalState,
        shareModalState,
        restoreModalState,
        markdownModalState,
        importModalState,
        catalogState,
        editorState,
        setMode,
        setDeleteModalState,
        setSaveConfirmModalState,
        setShareModalState,
        setRestoreModalState,
        setMarkdownModalState,
        setImportModalState,
        markNavigatedInAppRef,
      }}
    >
      {children}
    </CatalogContext.Provider>
  );
};

export const useCatalog = (): CatalogContextType => {
  const context = useContext(CatalogContext);
  if (!context) {
    throw new Error('useCatalog must be used within a CatalogProvider');
  }
  return context;
};
