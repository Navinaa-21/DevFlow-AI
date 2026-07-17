export interface User {
  id: string;
  full_name: string;
  email: string;
  avatar_url: string | null;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceListResponse {
  items: Workspace[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExternalRepository {
  provider_repo_id: string;
  provider: "GITHUB";
  name: string;
  full_name: string;
  repo_url: string;
  default_branch: string;
  description: string | null;
  private: boolean;
  is_connected: boolean;
}

export interface Repository {
  id: string;
  workspace_id: string;
  provider: "GITHUB";
  provider_repo_id: string;
  name: string;
  full_name: string;
  repo_url: string;
  default_branch: string;
  visibility?: string;
  last_synced_at?: string | null;
  webhook_enabled: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginInputs {
  email: string;
  password: string;
  rememberMe: boolean;
}

export interface RegisterInputs {
  full_name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

