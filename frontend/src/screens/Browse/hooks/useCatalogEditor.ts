/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import type { FormMode, FormSchema } from '@/components/browse';

export function useEditorState() {
  const [isEditorActive, setIsEditorActive] = useState<boolean>(false);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [createFilterType, setCreateFilterType] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<any>(null);
  const [viewingItem, setViewingItem] = useState<any>(null);
  const [formSchema, setFormSchema] = useState<FormSchema | null>(null);

  return {
    isEditorActive,
    formMode,
    createFilterType,
    editingItem,
    viewingItem,
    formSchema,
    setIsEditorActive,
    setFormMode,
    setCreateFilterType,
    setEditingItem,
    setViewingItem,
    setFormSchema,
  };
}

export type EditorStateType = ReturnType<typeof useEditorState>;
