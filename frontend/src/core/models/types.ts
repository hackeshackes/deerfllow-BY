export interface Model {
  name: string;
  model: string;
  display_name: string;
  description?: string | null;
  use?: string | null;
  base_url?: string | null;
  api_key?: string | null;
  temperature?: number | null;
  supports_thinking?: boolean;
  supports_reasoning_effort?: boolean;
  supports_vision?: boolean;
  enabled?: boolean;
  is_default?: boolean;
}
