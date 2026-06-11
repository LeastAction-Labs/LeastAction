/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
export interface VersionCompatibility {
  core?: string[];
  python?: string;
  la_interface?: string;
}

type VersionTuple = [number, number, number];

const OPERATORS = ['>=', '<=', '!=', '>', '<'] as const;

function parsePattern(pattern: string): { op: string | null; v: VersionTuple } | null {
  let op: string | null = null;
  let rest = pattern.trim();

  for (const candidate of OPERATORS) {
    if (rest.startsWith(candidate)) {
      op = candidate;
      rest = rest.slice(candidate.length);
      break;
    }
  }

  // Wildcard major: "1.*" — only major matters, op must be null
  if (op === null && rest.endsWith('.*')) {
    const major = parseInt(rest.slice(0, -2), 10);
    if (isNaN(major)) return null;
    return { op: 'major-only', v: [major, 0, 0] };
  }

  const parts = rest.split('.').map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return null;
  return { op, v: parts as VersionTuple };
}

function compareTuples(a: VersionTuple, b: VersionTuple): number {
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] - b[i];
  }
  return 0;
}

function patternMatches(pattern: string, core: VersionTuple): boolean {
  const parsed = parsePattern(pattern);
  if (!parsed) return false;
  const { op, v } = parsed;
  if (op === 'major-only') return core[0] === v[0];
  const cmp = compareTuples(core, v);
  if (op === null) return cmp === 0;
  if (op === '>=') return cmp >= 0;
  if (op === '>') return cmp > 0;
  if (op === '<=') return cmp <= 0;
  if (op === '<') return cmp < 0;
  if (op === '!=') return cmp !== 0;
  return false;
}

function parseCoreVersion(v: string): VersionTuple | null {
  const parts = v.split('.').map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) return null;
  return parts as VersionTuple;
}

/**
 * Returns true if coreVersion satisfies ALL patterns in version_compatibility.core.
 *
 * Rules:
 * - version_compatibility absent → compatible (no constraint)
 * - core array empty             → compatible with all versions
 * - otherwise                   → ALL patterns must pass (AND logic)
 *
 * Supported patterns: ">=1.0.0", ">1.0.0", "<=2.0.0", "<2.0.0", "!=1.5.0",
 *                     "1.2.3" (exact), "1.*" (major-only wildcard)
 */
export function isCoreCompatible(
  versionCompatibility: VersionCompatibility | null | undefined,
  coreVersion: string,
): boolean {
  const patterns = versionCompatibility?.core ?? [];
  if (patterns.length === 0) return true;

  const core = parseCoreVersion(coreVersion);
  if (!core) return false;

  return patterns.every((p) => patternMatches(p, core));
}

/**
 * Returns a human-readable incompatibility message, or null if compatible.
 */
export function compatibilityMessage(
  versionCompatibility: VersionCompatibility | null | undefined,
  coreVersion: string,
): string | null {
  if (isCoreCompatible(versionCompatibility, coreVersion)) return null;
  const patterns = versionCompatibility?.core ?? [];
  return `Requires core ${patterns.join(', ')} (you have ${coreVersion})`;
}
