import { getBackendBaseURL } from "@/core/config";

import type { MCPConfig, MCPServerConfig, MCPPreset, ChannelStatus, ChannelConfig } from "./types";

export async function loadMCPConfig(): Promise<MCPConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`);
  return response.json();
}

export async function updateMCPConfig(config: MCPConfig): Promise<MCPConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  return response.json();
}

export async function loadMCPPresets(): Promise<{ presets: MCPPreset[] }> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/presets`);
  return response.json();
}

export async function testMCPServer(serverConfig: MCPServerConfig): Promise<{ success: boolean; error?: string }> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/servers/test`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(serverConfig),
  });
  return response.json();
}

export async function getMCPServerStatus(serverName: string): Promise<{ connected: boolean; error?: string }> {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/servers/${encodeURIComponent(serverName)}/status`);
  return response.json();
}

export async function loadChannelStatus(): Promise<ChannelStatus> {
  const response = await fetch(`${getBackendBaseURL()}/api/channels/`);
  return response.json();
}

export async function loadChannelConfig(): Promise<ChannelConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/channels/config`);
  return response.json();
}

export async function restartChannel(name: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${getBackendBaseURL()}/api/channels/${encodeURIComponent(name)}/restart`, {
    method: "POST",
  });
  return response.json();
}
