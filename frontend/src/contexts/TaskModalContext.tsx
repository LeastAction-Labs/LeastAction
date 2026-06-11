/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';
import React, { createContext, useContext, useState } from 'react';

export enum TaskModalMode {
  CREATE = 'create',
  RUN = 'run',
  SCHEDULE = 'schedule',
  EDIT = 'edit',
}

export enum TaskModalScopeType {
  OPERATOR = 'operator',
  PAYLOAD = 'payload',
  CONNECTION = 'connection',
  AI = 'ai',
  DEFAULT = 'default',
  TASK = 'task',
}

export interface OperatorData {
  codeblock: object;
  bashblock: object;
  prompt?: string;
  install_docs: object;
  guide_docs: object;
  connection?: object;
  payload?: string;
}

export interface TaskModalScope {
  scopeType: TaskModalScopeType;
  operatorLaui?: string;
  payloadValue?: string;
  payloadLaui?: string;
  connectionLaui?: string;
}

export interface TaskData {
  laui?: string;
  name?: string;
  description?: string;
  account_laui?: string;
  project_laui?: string;
  workflow_laui?: string;
  operator_laui?: string;
  connection_laui?: string;
  payload?: string;
  payload_laui?: string;
  config?: string;
  attached_config_lauis?: string[];
  actions?: Record<string, any[]>;
  logical_date?: string;
  frequency?: string;
  start_date?: string;
  end_date?: string;
  [key: string]: any;
}

export interface TaskModalData {
  isOpen: boolean;
  mode?: TaskModalMode;
  initialTaskData?: TaskData;
  scope?: TaskModalScope;
  operatorData?: OperatorData;
  onSuccess?: () => void;
}

interface TaskModalContextType {
  taskModalState: TaskModalData | null;
  setTaskModalState: (data: TaskModalData | null) => void;
}

const TaskModalContext = createContext<TaskModalContextType | undefined>(undefined);

export const TaskModalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [taskModalState, setTaskModalState] = useState<TaskModalData | null>(null);
  return (
    <TaskModalContext.Provider
      value={{
        taskModalState,
        setTaskModalState,
      }}
    >
      {children}
    </TaskModalContext.Provider>
  );
};

export const useTaskModalContext = (): TaskModalContextType => {
  const context = useContext(TaskModalContext);
  if (!context) {
    throw new Error('useTaskModalContext must be used within a TaskModalProvider');
  }
  return context;
};
