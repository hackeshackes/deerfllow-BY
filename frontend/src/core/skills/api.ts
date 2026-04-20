import { getBackendBaseURL } from "@/core/config";

import type { Skill, UserSkillConfig } from "./type";

export async function loadSkills() {
  const skills = await fetch(`${getBackendBaseURL()}/api/skills`);
  const json = await skills.json();
  return json.skills as Skill[];
}

export async function enableSkill(skillName: string, enabled: boolean) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/skills/${skillName}`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        enabled,
      }),
    },
  );
  return response.json();
}

export interface InstallSkillRequest {
  thread_id: string;
  path: string;
}

export interface InstallSkillResponse {
  success: boolean;
  skill_name: string;
  message: string;
}

export async function installSkill(
  request: InstallSkillRequest,
): Promise<InstallSkillResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/install`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    // Handle HTTP error responses (4xx, 5xx)
    const errorData = await response.json().catch(() => ({}));
    const errorMessage =
      errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`;
    return {
      success: false,
      skill_name: "",
      message: errorMessage,
    };
  }

  return response.json();
}

// User Skills API
export async function loadUserSkills(): Promise<UserSkillConfig[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/user/skills`);
  const json = await response.json();
  return json.skills as UserSkillConfig[];
}

export interface UpdateUserSkillConfigRequest {
  enabled?: boolean;
  is_default?: boolean;
  config?: Record<string, string>;
}

export async function updateUserSkillConfig(
  skillName: string,
  request: UpdateUserSkillConfigRequest,
): Promise<UserSkillConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/user/skills/${skillName}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return response.json();
}

export async function enableUserSkill(skillName: string): Promise<UserSkillConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/user/skills/${skillName}/enable`, {
    method: "POST",
  });
  return response.json();
}

export async function disableUserSkill(skillName: string): Promise<UserSkillConfig> {
  const response = await fetch(`${getBackendBaseURL()}/api/user/skills/${skillName}/disable`, {
    method: "POST",
  });
  return response.json();
}

// Skill Sharing API
export interface ShareSkillRequest {
  visibility: "public" | "workspace";
  workspace_id?: string;
}

export interface ShareSkillResponse {
  skill_name: string;
  visibility: string;
  workspace_id: string | null;
  owner_id: string | null;
}

export async function shareSkill(
  skillName: string,
  request: ShareSkillRequest,
): Promise<ShareSkillResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/${skillName}/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return response.json();
}

export async function unshareSkill(skillName: string): Promise<{ success: boolean }> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/${skillName}/unshare`, {
    method: "POST",
  });
  return response.json();
}

export interface RateSkillRequest {
  rating: number;
  comment?: string;
}

export async function rateSkill(
  skillName: string,
  request: RateSkillRequest,
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/${skillName}/rate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return response.json();
}

export interface SharedSkill {
  skill_name: string;
  visibility: string;
  workspace_id: string | null;
  owner_id: string | null;
}

export async function loadSharedSkills(): Promise<SharedSkill[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/shared`);
  const json = await response.json();
  return json.skills as SharedSkill[];
}

// Custom Skill Creation API
export interface CreateCustomSkillRequest {
  name: string;
  content: string;
}

export interface CustomSkillResponse {
  name: string;
  description: string;
  category: string;
  license: string | null;
  author: string | null;
  version: string | null;
  compatibility: string | null;
  enabled: boolean;
  source: string | null;
  installed_at: string | null;
  display_name_zh: string | null;
  description_zh: string | null;
  content: string;
}

export async function createCustomSkill(
  request: CreateCustomSkillRequest,
): Promise<CustomSkillResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/custom`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

export async function loadCustomSkills(): Promise<Skill[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/custom`);
  const json = await response.json();
  return json.skills as Skill[];
}

export async function loadMyCustomSkills(): Promise<Skill[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/custom/mine`);
  const json = await response.json();
  return json.skills as Skill[];
}

export async function deleteCustomSkill(skillName: string): Promise<void> {
  const response = await fetch(`${getBackendBaseURL()}/api/skills/custom/${skillName}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}: ${response.statusText}`);
  }
}
