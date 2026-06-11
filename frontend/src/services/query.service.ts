/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

const EXECUTE_URL = `${CORE_BACKEND_URL}/api/v1/query/execute`;

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
}

export async function executeQuery(connectionLaui: string, sql: string): Promise<QueryResult> {
  return httpJson<QueryResult>(EXECUTE_URL, {
    method: 'POST',
    body: { connection_laui: connectionLaui, sql },
  });
}
