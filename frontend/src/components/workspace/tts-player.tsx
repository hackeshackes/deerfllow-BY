"use client";

import { Loader2Icon, Volume2Icon } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import { synthesizeSpeech } from "@/lib/api/voice";

import { Tooltip } from "./tooltip";

interface TTSPlayerProps {
  text: string;
  className?: string;
}

export function TTSPlayer({ text, className }: TTSPlayerProps) {
  const { t } = useI18n();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playAudio = useCallback(async () => {
    if (!text || text.trim().length === 0) return;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    setIsLoading(true);
    try {
      const audioBuffer = await synthesizeSpeech(text);
      const blob = new Blob([audioBuffer], { type: "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setIsLoading(false);
        URL.revokeObjectURL(url);
      };

      audioRef.current = audio;
      await audio.play();
      setIsPlaying(true);
      setIsLoading(false);
    } catch {
      setIsLoading(false);
      setIsPlaying(false);
    }
  }, [text]);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const button = (
    <Button
      size="icon-sm"
      type="button"
      variant="ghost"
      className={className}
      onClick={isPlaying ? stopAudio : playAudio}
      disabled={isLoading}
    >
      {isLoading ? (
        <Loader2Icon className="size-4 animate-spin" />
      ) : isPlaying ? (
        <Volume2Icon className="size-4 animate-pulse" />
      ) : (
        <Volume2Icon className="size-4" />
      )}
    </Button>
  );

  return (
    <Tooltip content={t.voice.playAudio}>
      {button}
    </Tooltip>
  );
}