/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import MonacoEditor from '@monaco-editor/react';
import { Box } from '@mui/material';

const LINE_HEIGHT_PX = 19;
const MIN_LINES = 10;
const MAX_HEIGHT_PX = 1000;

function computeEditorHeight(content: string, maxHeight: number): string {
  const lineCount = (content || '').split('\n').length;
  const clampedLines = Math.max(MIN_LINES, lineCount);
  return `${Math.min(maxHeight, clampedLines * LINE_HEIGHT_PX)}px`;
}

interface MonacoWrapperProps {
  content: string;
  fileName?: string;
  readOnly?: boolean;
  field: any;
  onChange?: (value: string) => void;
  /** Fixed height string (e.g. "100%", "300px"). When set, overrides auto-sizing. */
  height?: string;
  /** Max height in px for auto-sizing. Defaults to 1000. Ignored when `height` is set. */
  maxHeight?: number;
}

const LANGUAGE_MAP: Record<string, string[]> = {
  python: ['.py', 'python'],
  javascript: ['.js', '.jsx', 'javascript'],
  typescript: ['.ts', '.tsx', 'typescript'],
  markdown: ['.md', '.markdown'],
  shell: ['.sh', '.bash', '.zsh'],
  yaml: ['.yaml', '.yml'],
  json: ['.json'],
  sql: ['.sql'],
  csv: ['.csv'],
  xml: ['.xml'],
  html: ['.html', '.htm'],
  css: ['.css'],
};

const styles = {
  monacoContainer: {
    border: 1,
    borderColor: 'var(--border)',
    borderRadius: 1,
  },
};

// Detect language from content
const detectLanguageFromContent = (content: string): string | null => {
  if (!content || typeof content !== 'string') return null;

  const trimmed = content.trim();
  if (!trimmed) return null;

  // JSON detection
  if (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']'))
  ) {
    try {
      JSON.parse(trimmed);
      return 'json';
    } catch {
      // Not valid JSON, continue checking
    }
  }

  // YAML detection
  const yamlPatterns = [
    /^---/m, // YAML document start
    /^\w+:\s*$/m, // Key with no value on same line
    /^\w+:\s+\S+/m, // Key: value pairs
    /^-\s+\w+/m, // List items
  ];
  if (yamlPatterns.some((pattern) => pattern.test(trimmed))) {
    // Make sure it's not JSON-like or code
    if (!trimmed.includes('{') && !trimmed.includes('[')) {
      return 'yaml';
    }
  }

  // SQL detection
  const sqlKeywords = [
    /\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|FROM|WHERE|JOIN|GROUP BY|ORDER BY)\b/i,
    /\b(TABLE|DATABASE|INDEX|VIEW|PROCEDURE|FUNCTION)\b/i,
  ];
  if (sqlKeywords.some((pattern) => pattern.test(trimmed))) {
    return 'sql';
  }

  // Python detection
  const pythonPatterns = [
    /^(import|from)\s+\w+/m, // import statements
    /^def\s+\w+\s*\(/m, // function definitions
    /^class\s+\w+/m, // class definitions
    /^if\s+__name__\s*==\s*['"]/m, // if __name__ == '__main__'
    /^\s*#\s*!/, // shebang for python
    /\bprint\s*\(/, // print function
  ];
  if (pythonPatterns.some((pattern) => pattern.test(trimmed))) {
    return 'python';
  }

  // JavaScript/TypeScript detection
  const jsPatterns = [
    /\b(const|let|var)\s+\w+/, // variable declarations
    /\b(function|async|await)\b/, // function keywords
    /=>\s*{/, // arrow functions
    /^import\s+.*\s+from\s+['"]/m, // ES6 imports
    /^export\s+(default|const|function|class)/m,
    /console\.(log|error|warn)/,
  ];
  if (jsPatterns.some((pattern) => pattern.test(trimmed))) {
    // Check for TypeScript specific patterns
    if (
      /:\s*(string|number|boolean|any|void|unknown)/.test(trimmed) ||
      /interface\s+\w+/.test(trimmed) ||
      /type\s+\w+\s*=/.test(trimmed)
    ) {
      return 'typescript';
    }
    return 'javascript';
  }

  // XML/HTML detection
  if (trimmed.startsWith('<') && trimmed.endsWith('>')) {
    if (/<html|<head|<body|<div|<span|<p>/i.test(trimmed)) {
      return 'html';
    }
    return 'xml';
  }

  // CSV detection
  const lines = trimmed.split('\n');
  if (lines.length >= 2) {
    const firstLine = lines[0];
    if (firstLine.includes(',')) {
      const commaCount = (firstLine.match(/,/g) || []).length;
      const consistentCommas = lines.slice(0, Math.min(5, lines.length)).every((line) => {
        const count = (line.match(/,/g) || []).length;
        return count === commaCount;
      });
      if (consistentCommas) {
        return 'csv';
      }
    }
  }

  // Shell script detection
  const shellPatterns = [
    /^#!/, // shebang
    /\becho\s+/, // echo command
    /\bif\s+\[.*\]\s*;?\s*then/, // if statements
    /\b(export|source|alias)\s+/, // common shell commands
  ];
  if (shellPatterns.some((pattern) => pattern.test(trimmed))) {
    return 'shell';
  }

  // Markdown detection
  const markdownPatterns = [
    /^#{1,6}\s+/m, // Headers
    /^\*\*.*\*\*$/m, // Bold
    /^\*.*\*$/m, // Italic
    /^\[.*\]\(.*\)/m, // Links
    /^```/m, // Code blocks
    /^[-*+]\s+/m, // Lists
  ];
  const markdownCount = markdownPatterns.filter((pattern) => pattern.test(trimmed)).length;
  if (markdownCount >= 2) {
    return 'markdown';
  }

  return 'sql';
};

// Get language from filename
const getLanguageFromFileName = (name: string = ''): string | null => {
  const search = name.toLowerCase();

  for (const [lang, patterns] of Object.entries(LANGUAGE_MAP)) {
    if (patterns.some((p) => search.includes(p))) {
      return lang;
    }
  }

  return 'sql';
};

export const MonacoWrapper = ({
  content,
  fileName,
  readOnly = false,
  field,
  onChange,
  height: heightProp,
  maxHeight = MAX_HEIGHT_PX,
}: MonacoWrapperProps) => {
  const height = heightProp ?? computeEditorHeight(content, maxHeight);

  const getLanguage = () => {
    // 2. Try to detect from filename first
    const fileNameLang = getLanguageFromFileName(fileName || field.name || '');
    if (fileNameLang) {
      return fileNameLang;
    }

    // 3. Try to detect from content
    const contentLang = detectLanguageFromContent(content);
    if (contentLang) {
      return contentLang;
    }

    // 4. Default to plaintext
    return 'sql';
  };

  return (
    <Box sx={{ ...styles.monacoContainer, height, minHeight: height, overflow: 'hidden' }}>
      <MonacoEditor
        height="100%"
        language={getLanguage()}
        value={content || ''}
        theme="vs-dark"
        onChange={(v) => onChange?.(v || '')}
        options={{
          readOnly,
          domReadOnly: readOnly,
          fontSize: field.fontSize || 12,
          minimap: { enabled: !readOnly && field.minimap !== false },
          wordWrap: field.wordWrap !== false ? 'on' : 'off',
          lineNumbers: field.lineNumbers !== false ? 'on' : 'off',
          automaticLayout: true,
          formatOnType: readOnly ? false : field.formatOnType !== false,
          formatOnPaste: readOnly ? false : field.formatOnPaste !== false,
          scrollbar: {
            alwaysConsumeMouseWheel: false,
          },
        }}
      />
    </Box>
  );
};
