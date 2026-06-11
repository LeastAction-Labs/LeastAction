/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { CORE_BACKEND_URL } from '@/config/urls';

import { httpJson } from './api';

const EMBED_URL = `${CORE_BACKEND_URL}/api/v1/embed/token`;

export interface EmbedToken {
  embed_url: string;
  embed_token?: string; // Power BI only — passed to the powerbi-client SDK
  expires_in: number;
}

export async function getEmbedToken(itemLaui: string): Promise<EmbedToken> {
  return httpJson<EmbedToken>(EMBED_URL, {
    method: 'POST',
    body: { item_laui: itemLaui },
  });
}
