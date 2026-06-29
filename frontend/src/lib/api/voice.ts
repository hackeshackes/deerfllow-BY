/**
 * Voice API client — TTS synthesis + STT config CRUD.
 *
 * The module was missing from the codebase but referenced by
 * `voice-admin-page.tsx` and `tts-player.tsx`; this file restores the
 * client without changing either caller's signature.
 */
export interface VoiceConfig {
  stt_enabled: boolean;
  tts_enabled: boolean;
  stt_language: string;
  stt_model_size: string;
  tts_voice: string;
  tts_speed: number;
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    credentials: "include",
  });
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

export async function getVoiceConfig(): Promise<VoiceConfig> {
  return fetchJSON<VoiceConfig>("/api/voice/config");
}

export async function updateVoiceConfig(config: VoiceConfig): Promise<VoiceConfig> {
  return fetchJSON<VoiceConfig>("/api/voice/config", {
    method: "PUT",
    body: JSON.stringify(config),
  });
}

/**
 * Synthesize `text` to MP3 audio. Returns the raw bytes as an
 * `ArrayBuffer` so the caller can wrap it in a `Blob` / `Audio`.
 */
export async function synthesizeSpeech(text: string): Promise<ArrayBuffer> {
  const resp = await fetch("/api/voice/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ text }),
  });
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${await resp.text()}`);
  }
  return resp.arrayBuffer();
}
