/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
export type AIItemType = 'action' | 'agent' | 'generate' | 'operator' | 'payload';
export type AIProvider = 'anthropic' | 'openai' | 'azure';
export type AIProviderConfig = {
  name: string;
  code: string;
  description: string;
};
export interface AIConfigType {
  aiProvider: string;
  aiChatLaui: string;
  aiChatName: string;
  includeGuideDoc: boolean;
  includeInstallGuide: boolean;
}
export interface AIFormState {
  currentStep: number;
  itemType: AIItemType | null;
  creationMethod: 'ai' | 'manual';
  aiProvider: AIProvider | null;
  connectionId: string | null;
  includeGuideDoc: boolean;
  includeInstallGuide: boolean;
  prompt: string;
  generatedContent: {
    codeblock?: Record<string, string>;
    bashblock?: Record<string, string>;
    connection?: Record<string, string>;
    guide?: Record<string, string>;
    install_guide?: Record<string, string>;
  } | null;
}

export interface Connection {
  laui: string;
  name: string;
  item_type: string;
  provider: string;
  data?: any;
}

export interface Payload {
  laui: string;
  name: string;
  item_type: string;
  data?: any;
}

export interface Workflow {
  laui: string;
  name: string;
  item_type: string;
  data?: any;
}

// API Response Types
export interface AIGenerationResponse {
  message: string;
  generated_content: {
    codeblock?: Record<string, string>;
    bashblock?: Record<string, string>;
    connection?: Record<string, string>;
    guide?: Record<string, string>;
    install_guide?: Record<string, string>;
  };
  token_limit_exceeded: boolean;
  partial_generation: boolean;
  temp_file_path?: string;
}
