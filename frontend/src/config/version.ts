/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
const LS_KEY = 'la_core_version';

export function getCoreVersion(): string {
  return localStorage.getItem(LS_KEY) ?? (import.meta as any).env?.VITE_CORE_VERSION ?? '0.0.0';
}

export function setCoreVersion(v: string): void {
  localStorage.setItem(LS_KEY, v);
}
