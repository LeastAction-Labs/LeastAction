/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box } from '@mui/material';

import { AIMode, useAI } from '@/contexts/AIContext';

import { generateAIContent } from '../../services/ai.service';
import { LeftSidebar, TopHeader } from '../browse';
import AIConfig from './slides/AIConfig';
import ItemType from './slides/ItemType';
import ManualEditor from './slides/ManualEditor';
import ManualItem from './slides/ManualItem';

const styles = {
  container: {
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
};

export default function AIWizard() {
  const { mode, config, itemType, sessionId } = useAI();

  const handleGenerate = async (
    prompt: string,
    includeGuideDoc: boolean,
    includeInstallGuide: boolean,
    messages?: { role: string; content: string }[],
    generatedContent?: Record<string, any>,
    skillContent?: string,
  ) => {
    if (!config) return;
    const { aiProvider, aiChatLaui, connectionLaui } = config;

    return await generateAIContent({
      prompt,
      chat_laui: aiChatLaui,
      item_type: itemType,
      ai_provider: aiProvider,
      include_guide_doc: includeGuideDoc,
      include_install_guide: includeInstallGuide,
      messages,
      generated_content: generatedContent,
      skill_content: skillContent,
      ...(sessionId ? { session_id: sessionId } : {}),
      ...(connectionLaui ? { connection_laui: connectionLaui } : {}),
    });
  };

  return (
    <Box sx={styles.container}>
      <TopHeader />
      <Box sx={styles.mainContent}>
        <LeftSidebar />
        {mode === AIMode.ITEMTYPE ? (
          <ItemType />
        ) : mode === AIMode.AICONFIG ? (
          <AIConfig />
        ) : mode === AIMode.MANUALEDITOR ? (
          <ManualEditor onGenerate={handleGenerate} />
        ) : (
          <ManualItem />
        )}
      </Box>
    </Box>
  );
}
