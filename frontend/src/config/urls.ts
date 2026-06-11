/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// core Backend (this application's backend)
// Empty default → relative URLs → calls hit the same origin the SPA was served
// from (nginx proxies /api/ and /mcp/ to the backend in production). For local
// `npm run dev`, frontend/.env sets VITE_API_BASE_URL=http://localhost:8000.
export const CORE_BACKEND_URL = import.meta.env.VITE_API_BASE_URL ?? '';
export const CORE_API_URL = `${CORE_BACKEND_URL}/api/v1`;

// Marketplace
export const MARKETPLACE_URL = 'https://dev.leastactionlabs.com';

// core Frontend (this application) — defaults to wherever the SPA is served from.
export const CORE_FRONTEND_URL = import.meta.env.VITE_FRONTEND_URL ?? window.location.origin;
