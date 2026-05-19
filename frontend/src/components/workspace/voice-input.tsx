"use client";

import { MicIcon, SquareIcon, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";

interface VoiceInputProps {
  className?: string;
  onTranscriptionChange?: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInput({
  className,
  onTranscriptionChange,
  disabled,
}: VoiceInputProps) {
  const { t } = useI18n();
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());

        if (audioChunksRef.current.length === 0) {
          return;
        }

        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });

        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append("file", audioBlob, "recording.webm");

          const response = await fetch(
            `${getBackendBaseURL()}/api/voice/stt`,
            {
              method: "POST",
              body: formData,
              headers: {
                Accept: "application/json",
              },
            },
          );

          if (!response.ok) {
            throw new Error(`STT request failed: ${response.status}`);
          }

          const data = (await response.json()) as { text?: string };
          const transcribedText = data.text?.trim() || "";

          if (transcribedText) {
            onTranscriptionChange?.(transcribedText);
          } else {
            toast.warning(t.voice.noSpeechDetected);
          }
        } catch (error) {
          console.error("Transcription error:", error);
          toast.error(t.voice.transcriptionFailed);
        } finally {
          setIsTranscribing(false);
          setDuration(0);
          setAudioLevel(0);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100);

      setIsRecording(true);
      setDuration(0);

      timerRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);

      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const updateLevel = () => {
        if (analyserRef.current) {
          const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
          analyserRef.current.getByteFrequencyData(dataArray);
          const average =
            dataArray.reduce((a, b) => a + b, 0) / dataArray.length / 255;
          setAudioLevel(average);
        }
        animationRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
    } catch (error) {
      console.error("Failed to start recording:", error);
      toast.error(t.voice.microphoneAccessFailed);
    }
  }, [onTranscriptionChange, t.voice.microphoneAccessFailed, t.voice.noSpeechDetected, t.voice.transcriptionFailed]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setAudioLevel(0);
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  if (isTranscribing) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className={cn("relative px-2", className)}
        disabled
      >
        <Loader2Icon className="size-4 animate-spin" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn(
        "relative px-2 transition-all duration-200",
        isRecording && "bg-red-500/10 text-red-500",
        className,
      )}
      onClick={toggleRecording}
      disabled={disabled}
      title={isRecording ? t.voice.stopRecording : t.voice.startRecording}
    >
      {isRecording ? (
        <>
          <div className="absolute inset-0 flex items-center justify-center rounded-full">
            <div
              className="bg-red-500 rounded-full animate-ping"
              style={{
                width: `${Math.max(16, audioLevel * 40 + 16)}px`,
                height: `${Math.max(16, audioLevel * 40 + 16)}px`,
                opacity: 0.3,
              }}
            />
          </div>
          <SquareIcon className="size-3 fill-current" />
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-red-500 font-mono">
            {formatDuration(duration)}
          </span>
        </>
      ) : (
        <MicIcon className="size-4" />
      )}
    </Button>
  );
}