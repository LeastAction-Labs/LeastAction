/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Shared TypeScript types for FieldRenderer components

export interface ArrayItem {
  fileName: string;
  content: string;
}

export interface FieldRendererProps {
  field: any;
  value: any;
  mode: 'create' | 'edit' | 'view';
  onChange: (fieldName: string, value: any) => void;
  itemData: any;
}

export interface FieldConfig {
  editorType: string;
  editorMonacoFormat: string;
  defaultFileName: string;
  placeholder: string;
  fileNamePlaceholder: string;
  monacoHeight: string;
  textAreaRows: { min: number; max: number };
  arrayTextAreaRows: { min: number; max: number };
}
