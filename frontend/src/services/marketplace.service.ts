/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { FullItemData } from '@/components/browse';

import { MARKETPLACE_URL } from '../config/urls';
import { httpJson } from './api';

const API_ENDPOINTS = {
  login: MARKETPLACE_URL + '/api/v1/marketplace/auth/login',
  logout: MARKETPLACE_URL + '/api/v1/marketplace/auth/logout',
  signup: MARKETPLACE_URL + '/api/v1/marketplace/auth/signup',
  check: MARKETPLACE_URL + '/api/v1/marketplace/catalog/check',
  buy_license: MARKETPLACE_URL + '/api/v1/marketplace/license/buy',
  user_me: MARKETPLACE_URL + '/api/v1/marketplace/user/me',
  publish: MARKETPLACE_URL + '/api/v1/marketplace/catalog/create',
};

interface MarketplaceLoginRequest {
  email: string;
  password: string;
}

export async function marketplaceLogin(request: MarketplaceLoginRequest): Promise<any> {
  const data = await httpJson<any>(API_ENDPOINTS.login, {
    method: 'POST',
    body: request as unknown as Record<string, unknown>,
  });
  return data;
}

interface MarketplaceSignupRequest {
  username: string;
  email: string;
  password: string;
}

export async function marketplaceSignup(request: MarketplaceSignupRequest): Promise<any> {
  const data = await httpJson<any>(API_ENDPOINTS.signup, {
    method: 'POST',
    body: request as unknown as Record<string, unknown>,
  });
  return data;
}

export async function marketplaceCheckLoggedIn(): Promise<any> {
  const data = await httpJson<any>(API_ENDPOINTS.check, {
    method: 'GET',
  });
  return data;
}

export interface LicenseBuyRequest {
  total_users: number;
  duration: number;
}

export interface LicenseResponse {
  license_id: string;
  public_key: string;
}

export async function buyLicense(request: LicenseBuyRequest): Promise<LicenseResponse> {
  return await httpJson(API_ENDPOINTS.buy_license, {
    method: 'POST',
    body: request as unknown as Record<string, unknown>,
  });
}

export async function marketplaceLogout() {
  return await httpJson(API_ENDPOINTS.logout, {
    method: 'POST',
  });
}

export async function requestPublish() {
  return await httpJson(API_ENDPOINTS.user_me, {
    method: 'PATCH',
    body: { publish_requested: true },
  });
}

export interface MarketplaceUser {
  laui: string;
  username: string;
  email: string;
  role: 'user' | 'publisher' | 'admin';
  publish_requested: boolean;
  system_user_laui?: string | null;
}

export async function getMarketplaceUser(): Promise<MarketplaceUser> {
  return await httpJson<MarketplaceUser>(`${API_ENDPOINTS.user_me}`);
}

export async function publishItem(item: FullItemData | Record<string, any>) {
  return await httpJson(API_ENDPOINTS.publish, {
    method: 'POST',
    body: Object.fromEntries(Object.entries(item).filter(([_, v]) => v != null)),
  });
}
