/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

const VALIDATE_URL = `${CORE_BACKEND_URL}/api/v1/catalog/validate`;

export interface CodeblockValidationEntry {
  code: string;
  message: string;
  file: string | null;
  line: number | null;
}

export interface ValidationResult {
  valid: boolean;
  errors: CodeblockValidationEntry[];
  warnings: CodeblockValidationEntry[];
}

export async function validateCodeblock(
  codeblock: Record<string, string>,
  itemType: string,
): Promise<ValidationResult> {
  return await httpJson<ValidationResult>(VALIDATE_URL, {
    method: 'POST',
    body: { codeblock, item_type: itemType },
  });
}

export function formatValidationForClipboard(result: ValidationResult): string {
  const lines: string[] = [];
  if (result.errors.length > 0) {
    lines.push(`Errors (${result.errors.length}):`);
    for (const e of result.errors) {
      const loc = [e.file, e.line].filter(Boolean).join(':');
      lines.push(`- [${e.code}] ${e.message}${loc ? ` (${loc})` : ''}`);
    }
  }
  if (result.warnings.length > 0) {
    if (lines.length) lines.push('');
    lines.push(`Warnings (${result.warnings.length}):`);
    for (const w of result.warnings) {
      const loc = [w.file, w.line].filter(Boolean).join(':');
      lines.push(`- [${w.code}] ${w.message}${loc ? ` (${loc})` : ''}`);
    }
  }
  return lines.join('\n');
}
