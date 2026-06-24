export type OIDCProviderType = "keycloak" | "okta" | "azure_ad" | "authing" | "generic";

export interface OIDCProvider {
  id: string;
  name: string;
  type: OIDCProviderType;
  issuer_url: string;
  client_id: string;
  enabled: boolean;
  created_at: string;
}

export interface OIDCProviderCreate {
  name: string;
  type: OIDCProviderType;
  issuer_url: string;
  client_id: string;
  client_secret: string;
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_id: string;
  actor_type: "user" | "system" | "automation" | "channel";
  action: string;
  resource_type: string;
  resource_id: string | null;
  workspace_id: string | null;
  success: boolean;
  metadata: Record<string, unknown>;
}

export interface Role {
  id: string;
  name: string;
  scope: "system" | "department" | "project";
  description: string | null;
}
