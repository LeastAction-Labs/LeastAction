/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Pure helper functions for JSON field type detection.
// Used by both FancyJsonEditor and ModalForm.

export type DataType = 'string' | 'number' | 'boolean' | 'array' | 'object' | 'null';

export const getDataType = (value: any): DataType => {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  if (typeof value === 'object') return 'object';
  if (typeof value === 'boolean') return 'boolean';
  if (typeof value === 'number') return 'number';
  return 'string';
};

export const isLockedValue = (value: any): boolean => {
  if (typeof value !== 'string') return false;
  return /^\{\{.+\}\}$/.test(value);
};

// Matches "_laui", "laui", "_lauis", "lauis" at end, or key === 'action'.
// Returns false if value is locked.
export const isLauiKey = (key: string, value?: any): boolean => {
  if (value !== undefined && isLockedValue(value)) return false;
  if (key === 'action') return true;
  return key !== 'parent_laui' && /_?lauis?$/i.test(key);
};

export const getItemTypeFromKey = (key: string): string => {
  if (key === 'action') return 'action';
  const normalizedKey = key.toLowerCase().replace(/[_\s]/g, '');

  if (normalizedKey === 'accountlaui') return 'folder.account';
  if (normalizedKey === 'projectlaui') return 'folder.project';
  if (normalizedKey === 'workflowfolderlaui' || normalizedKey === 'workflowlaui')
    return 'folder.workflow';

  const match = key.match(/^(.+?)(_?lauis?)$/i);
  if (match) return match[1].toLowerCase();

  return key.replace(/_?lauis?$/i, '').toLowerCase();
};

export const createArrayTemplate = (item: any): any => {
  if (item === null || item === undefined) return '';

  const itemType = getDataType(item);

  if (itemType === 'object') {
    const template: Record<string, any> = {};
    Object.keys(item).forEach((k) => {
      const v = item[k];
      if (isLockedValue(v)) {
        template[k] = v;
      } else {
        const vType = getDataType(v);
        if (vType === 'string') template[k] = '';
        else if (vType === 'number') template[k] = 0;
        else if (vType === 'boolean') template[k] = false;
        else if (vType === 'object') template[k] = createArrayTemplate(v);
        else if (vType === 'array') template[k] = [];
        else template[k] = '';
      }
    });
    return template;
  } else if (itemType === 'string') {
    return isLockedValue(item) ? item : '';
  } else if (itemType === 'number') {
    return 0;
  } else if (itemType === 'boolean') {
    return false;
  } else if (itemType === 'array') {
    return [];
  }

  return '';
};
