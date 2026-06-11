/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * System Service - Loads connection/operator mapping from config/system.yml
 * (same pattern as schema.service for config-driven dropdowns)
 */
// Path from frontend/src/services to repo config (same as schema.service)
import systemYaml from '../../../config/system.yml';

export type ConnectionOperatorMapping = Record<string, string[]>;

export type SystemConfig = {
  connection_operator_mapping?: ConnectionOperatorMapping;
  [key: string]: unknown;
};

const systemConfig: SystemConfig = (systemYaml as SystemConfig) ?? {};

const CONNECTION_PREFIX = 'connection.';
const OPERATOR_PREFIX = 'operator.';

function getMapping(): ConnectionOperatorMapping {
  const mapping = systemConfig.connection_operator_mapping;
  return mapping && typeof mapping === 'object' ? mapping : {};
}

/**
 * Connection subtypes from connection_operator_mapping keys (e.g. AWSIAMRole, python, docker).
 */
export function getConnectionSubtypes(): string[] {
  const mapping = getMapping();
  return Object.keys(mapping)
    .filter((k) => k.startsWith(CONNECTION_PREFIX))
    .map((k) => k.slice(CONNECTION_PREFIX.length))
    .filter(Boolean);
}

/**
 * Unique operator subtypes from all values in connection_operator_mapping (e.g. python, spark, docker).
 */
export function getOperatorSubtypes(): string[] {
  const mapping = getMapping();
  const set = new Set<string>();
  for (const arr of Object.values(mapping)) {
    if (!Array.isArray(arr)) continue;
    for (const v of arr) {
      if (typeof v === 'string' && v.startsWith(OPERATOR_PREFIX)) {
        set.add(v.slice(OPERATOR_PREFIX.length));
      }
    }
  }
  return [...set];
}

/**
 * Get subtype options for connection or operator create forms.
 */
export function getSubtypesFor(baseType: 'connection' | 'operator'): string[] {
  if (baseType === 'connection') return getConnectionSubtypes();
  if (baseType === 'operator') return getOperatorSubtypes();
  return [];
}
