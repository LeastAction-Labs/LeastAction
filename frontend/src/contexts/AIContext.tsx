/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { createContext, useContext, useState } from 'react';

import type { ReactNode } from '@tanstack/react-router';

import type AIConfig from '@/components/ai/slides/AIConfig';

export enum AIItemType {
  PAYLOAD = 'payload',
  ACTION = 'action',
  GENERATE = 'generate',
  AGENT = 'agent',
  OPERATOR = 'operator',
}

export enum AIMode {
  ITEMTYPE = 'itemType',
  AICONFIG = 'aiConfig',
  MANUALEDITOR = 'manualEditor',
  MANUALITEM = 'manaulItem',
}

export interface AIConfig {
  aiChatLaui: string;
  aiChatName: string;
  aiProvider: string;
  connectionLaui?: string;
  connectionName?: string;
  includeGuideDoc: boolean;
  includeInstallGuide: boolean;
}

export interface SaveItemModalState {
  isOpen: boolean;
  itemData?: any;
}

export interface AIHistorySession {
  laui: string;
  name: string;
  created_item_type: string;
  ai_provider?: string;
  chat_laui?: string;
  chat_name?: string;
  messages?: any[];
  generated_content?: any;
  latestPrompt?: string;
}

export interface AIContextType {
  itemType: AIItemType;
  mode: AIMode;
  config: AIConfig | null;
  saveItemModalState: SaveItemModalState;
  sessionId: string | null;
  sessionLaui: string | null;
  userFolderLaui: string | null;
  setItemType: (data: AIItemType) => void;
  setMode: (data: AIMode) => void;
  setConfig: (data: AIConfig) => void;
  setSaveItemModalState: (data: SaveItemModalState) => void;
  setSessionId: (id: string | null) => void;
  setSessionLaui: (laui: string | null) => void;
  setUserFolderLaui: (laui: string | null) => void;
}

const AIContext = createContext<AIContextType | undefined>(undefined);

export const AIProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [itemType, setItemType] = useState<AIItemType>(AIItemType.ACTION);
  const [mode, setMode] = useState<AIMode>(AIMode.ITEMTYPE);
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [saveItemModalState, setSaveItemModalState] = useState<SaveItemModalState>({
    isOpen: false,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionLaui, setSessionLaui] = useState<string | null>(null);
  const [userFolderLaui, setUserFolderLaui] = useState<string | null>(null);

  return (
    <AIContext.Provider
      value={{
        itemType,
        mode,
        config,
        saveItemModalState,
        sessionId,
        sessionLaui,
        userFolderLaui,
        setItemType,
        setMode,
        setConfig,
        setSaveItemModalState,
        setSessionId,
        setSessionLaui,
        setUserFolderLaui,
      }}
    >
      {children}
    </AIContext.Provider>
  );
};

export const useAI = (): AIContextType => {
  const context = useContext(AIContext);
  if (!context) {
    throw new Error('useAI must be used within a AIProvider');
  }
  return context;
};
