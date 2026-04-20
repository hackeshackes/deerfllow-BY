export interface MCPOAuthConfig {
  enabled: boolean;
  token_url: string;
  grant_type: "client_credentials" | "refresh_token";
  client_id: string | null;
  client_secret: string | null;
  refresh_token: string | null;
  scope: string | null;
  audience: string | null;
  token_field: string;
  token_type_field: string;
  expires_in_field: string;
  default_token_type: string;
  refresh_skew_seconds: number;
  extra_token_params: Record<string, string>;
}

export interface MCPServerConfig {
  enabled: boolean;
  type: "stdio" | "sse" | "http";
  command: string | null;
  args: string[];
  env: Record<string, string>;
  url: string | null;
  headers: Record<string, string>;
  oauth: MCPOAuthConfig | null;
  description: string;
}

export interface MCPConfig {
  mcp_servers: Record<string, MCPServerConfig>;
}

export interface MCPPreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  server: Partial<MCPServerConfig>;
}

export interface ChannelStatus {
  service_running: boolean;
  channels: Record<string, {
    enabled: boolean;
    running: boolean;
  }>;
}

export interface ChannelConfig {
  feishu: Record<string, unknown> | null;
  slack: Record<string, unknown> | null;
  telegram: Record<string, unknown> | null;
  wecom: Record<string, unknown> | null;
}

export interface ChannelInfo {
  id: string;
  name: string;
  icon: string;
  description: string;
  configFields: string[];
}
