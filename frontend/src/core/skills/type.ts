export interface Skill {
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
}

export interface CustomSkill {
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

export interface UserSkillConfig {
  skill_name: string;
  display_name: string;
  description: string;
  enabled: boolean;
  is_default: boolean;
  config: Record<string, string>;
  average_rating: number | null;
}
