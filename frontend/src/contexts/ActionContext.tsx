/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useState } from 'react';

import type { AttachedActions } from '@/screens/Browse/interfaces/Workflow';

export enum RunActionModalMode {
  CREATE = 'create',
  RUN = 'run',
}

export interface OperatorData {
  codeblock: object;
  bashblock: object;
  prompt: string;
  install_docs: object;
  guide_docs: object;
}

export interface RunActionModalDataType {
  actionLaui?: string;
  operatorData?: OperatorData;
  actionVariables: object;
  mode: RunActionModalMode;
  isOpen: boolean;
}

/*
create mode 
workflow laui

run mode 
uiActions and taskControl actions can be part of this 
*/

interface ActionContextType {
  runActionModalData: RunActionModalDataType | null;
  setRunActionModalData: (data: RunActionModalDataType | null) => void;
  showRunAction: boolean;
  setShowRunAction: (data: boolean) => void;
  attachedActions: AttachedActions | null;
  setAttachedActions: (data: AttachedActions | null) => void;
}

const ActionContext = createContext<ActionContextType | undefined>(undefined);

export const ActionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [runActionModalData, setRunActionModalData] = useState<RunActionModalDataType | null>(null);
  const [showRunAction, setShowRunAction] = useState<boolean>(false);
  const [attachedActions, setAttachedActions] = useState<AttachedActions | null>(null);
  return (
    <ActionContext.Provider
      value={{
        runActionModalData,
        setRunActionModalData,
        showRunAction,
        setShowRunAction,
        attachedActions,
        setAttachedActions,
      }}
    >
      {children}
    </ActionContext.Provider>
  );
};

export const useActionContext = (): ActionContextType => {
  const context = useContext(ActionContext);
  if (!context) {
    throw new Error('useActionContext must be used within a ActionProvider');
  }
  return context;
};
