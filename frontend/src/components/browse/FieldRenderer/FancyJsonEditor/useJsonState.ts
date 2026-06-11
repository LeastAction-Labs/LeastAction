/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

interface UseJsonStateProps {
  initialValue: any;
  fieldName: string;
  onChange: (fieldName: string, value: any) => void;
}

export interface JsonState {
  jsonText: string;
  parsedValue: Record<string, unknown>;
  parseError: string | null;
  handleMonacoChange: (text: string) => void;
  handleUiChange: (key: string, val: unknown) => void;
  handleAddKey: (key: string, val: unknown) => void;
  handleRemoveKey: (key: string) => void;
}

export function useJsonState({ initialValue, fieldName, onChange }: UseJsonStateProps): JsonState {
  const toText = (v: any): string => {
    if (typeof v === 'string') {
      // Already a JSON string (from getEditValue serialisation)
      try {
        JSON.parse(v);
        return v;
      } catch {
        return v;
      }
    }
    if (v == null) return '{}';
    return JSON.stringify(v, null, 2);
  };

  const [jsonText, setJsonText] = useState<string>(() => toText(initialValue));
  const [parseError, setParseError] = useState<string | null>(null);

  // Sync when the value prop changes externally (e.g. async data load)
  const prevExternalRef = useRef<string>(toText(initialValue));
  useEffect(() => {
    const incoming = toText(initialValue);
    if (incoming !== prevExternalRef.current) {
      prevExternalRef.current = incoming;
      setJsonText(incoming);
      setParseError(null);
    }
  }, [initialValue]);

  const parsedValue = useMemo<Record<string, unknown>>(() => {
    try {
      const parsed = JSON.parse(jsonText);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed as Record<string, unknown>;
      }
      return {};
    } catch {
      return {};
    }
  }, [jsonText]);

  const handleMonacoChange = useCallback(
    (text: string) => {
      setJsonText(text);
      try {
        const parsed = JSON.parse(text);
        setParseError(null);
        onChange(fieldName, parsed);
      } catch (e: any) {
        setParseError(e.message ?? 'Invalid JSON');
        // Don't propagate invalid JSON to parent — avoids cascading re-renders and flicker.
        // Parent retains the last valid value until JSON is fixed.
      }
    },
    [fieldName, onChange],
  );

  const commitObject = useCallback(
    (newObj: Record<string, unknown>) => {
      const text = JSON.stringify(newObj, null, 2);
      setJsonText(text);
      setParseError(null);
      onChange(fieldName, newObj);
    },
    [fieldName, onChange],
  );

  const handleUiChange = useCallback(
    (key: string, val: unknown) => {
      const newObj = { ...parsedValue, [key]: val };
      commitObject(newObj);
    },
    [parsedValue, commitObject],
  );

  const handleAddKey = useCallback(
    (key: string, val: unknown) => {
      if (!key.trim()) return;
      const newObj = { ...parsedValue, [key.trim()]: val };
      commitObject(newObj);
    },
    [parsedValue, commitObject],
  );

  const handleRemoveKey = useCallback(
    (key: string) => {
      const newObj = { ...parsedValue };
      delete newObj[key];
      commitObject(newObj);
    },
    [parsedValue, commitObject],
  );

  return {
    jsonText,
    parsedValue,
    parseError,
    handleMonacoChange,
    handleUiChange,
    handleAddKey,
    handleRemoveKey,
  };
}
