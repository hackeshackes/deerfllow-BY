export interface Model {
  name: string;
  model: string;
  display_name: string;
  description?: string | null;
  use?: string | null;
  base_url?: string | null;
  api_key?: string | null;
  request_timeout?: number;
  max_retries?: number;
  max_tokens?: number;
  temperature?: number | null;
  supports_thinking?: boolean;
  supports_reasoning_effort?: boolean;
  supports_vision?: boolean;
  use_responses_api?: boolean;
  output_version?: string | null;
  thinking?: Record<string, unknown> | null;
  when_thinking_enabled?: Record<string, unknown> | null;
  enabled?: boolean;
  is_default?: boolean;
}
