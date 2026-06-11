/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Marketplace search query parser.
 * Supports inline field:value syntax: publisher:"LeastAction" tag:"python" rest of query
 */

export interface ParsedMarketplaceQuery {
  /** Free-text portion of the query → passed as `name` filter */
  nameQuery: string;
  /** Structured field filters parsed from field:"value" or field:value tokens */
  fieldFilters: Record<string, string[]>;
}

/** Maps user-facing aliases to backend field names */
const FIELD_ALIASES: Record<string, string> = {
  tag: 'tags',
  tags: 'tags',
  category: 'category',
  division: 'division',
  publisher: 'publisher',
  type: 'item_type',
  item_type: 'item_type',
};

/** Matches field:"quoted value", field:"unclosed or field:unquoted tokens */
const FIELD_TOKEN_RE = /(\w+):"([^"]*)"?|(\w+):(\S+)/g;

/**
 * Parses a raw marketplace search string into a structured query.
 *
 * @example
 *   parseMarketplaceQuery('publisher:"LeastAction" tag:"python" tag:"ml" nlp tools')
 *   // → { nameQuery: "nlp tools", fieldFilters: { publisher: ["LeastAction"], tags: ["python", "ml"] } }
 */
export function parseMarketplaceQuery(raw: string): ParsedMarketplaceQuery {
  const fieldFilters: Record<string, string[]> = {};
  let remaining = raw;

  let match: RegExpExecArray | null;
  FIELD_TOKEN_RE.lastIndex = 0;

  const tokensToStrip: string[] = [];

  while ((match = FIELD_TOKEN_RE.exec(raw)) !== null) {
    const fieldRaw = match[1] ?? match[3];
    const value = match[2] ?? match[4];
    const backendField = FIELD_ALIASES[fieldRaw.toLowerCase()];
    if (backendField && value) {
      if (!fieldFilters[backendField]) fieldFilters[backendField] = [];
      fieldFilters[backendField].push(value);
      tokensToStrip.push(match[0]);
    }
  }

  for (const token of tokensToStrip) {
    remaining = remaining.replace(token, '');
  }

  return {
    nameQuery: remaining.trim(),
    fieldFilters,
  };
}

/**
 * Removes a specific field:value token (or all tokens for a field) from the raw query string.
 * Used when a user deletes an active filter chip.
 *
 * @example
 *   removeFieldFilter('tags:"python" tags:"ml" nlp', 'tags', 'python')
 *   // → 'tags:"ml" nlp'
 *   removeFieldFilter('publisher:"LeastAction" nlp', 'publisher')
 *   // → "nlp"
 */
export function removeFieldFilter(raw: string, backendField: string, value?: string): string {
  const aliases = Object.entries(FIELD_ALIASES)
    .filter(([, v]) => v === backendField)
    .map(([k]) => k);

  const allKeys = [...new Set([...aliases, backendField])].join('|');

  if (value != null) {
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(?:${allKeys}):"${escaped}"|(?:${allKeys}):${escaped}(?=\\s|$)`, 'gi');
    return raw
      .replace(re, '')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  const re = new RegExp(`(?:${allKeys}):"[^"]*"|(?:${allKeys}):\\S+`, 'gi');
  return raw
    .replace(re, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}
