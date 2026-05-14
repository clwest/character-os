import { useCallback, useEffect, useRef, useState } from "react";
import { Mic, UploadCloud, Wand2, X, Square, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useVoicePresets } from "@/lib/api/spokespeople";
import { cn } from "@/lib/utils";

const MAX_AUDIO_BYTES = 15 * 1024 * 1024; // 15 MB — matches backend cap
const ACCEPTED_MIMES: Record<string, true> = {
  "audio/mp3": true,
  "audio/mpeg": true,
  "audio/wav": true,
  "audio/x-wav": true,
  "audio/m4a": true,
  "audio/mp4": true,
  "audio/webm": true,
};
const MIN_RECORD_MS = 10_000; // Runway's documented floor
const MAX_RECORD_MS = 5 * 60 * 1000;

export type VoiceCaptureValue =
  | { mode: "preset"; preset: string }
  | {
      mode: "upload";
      dataUri: string;
      fileName: string;
      bytes: number;
      mime: string;
    }
  | {
      mode: "record";
      dataUri: string;
      bytes: number;
      mime: string;
      durationMs: number;
    };

interface VoiceCaptureProps {
  value: VoiceCaptureValue | null;
  onChange: (value: VoiceCaptureValue | null) => void;
  id?: string;
  className?: string;
}

/**
 * Three-mode voice capture for the spokesperson voice-clone flow.
 * Tabs:
 *
 *   - **Preset** — `<select>` over the supported Runway voice presets.
 *   - **Upload** — drag-and-drop / file picker. mp3 / wav / m4a / webm,
 *     15 MB cap (matches backend MAX_AUDIO_BYTES).
 *   - **Record** — `MediaRecorder` capture. 10 s floor (Runway), 5 min
 *     ceiling. Hidden when MediaRecorder isn't available.
 *
 * The component is stateful only for the input UX — it does not call
 * the API. The parent decides what to do with the chosen value.
 * Mirrors the SESSION 124 `<PortraitUpload>` shape so the wizard's
 * Step 3 inherits the same control pattern.
 */
export function VoiceCapture({
  value,
  onChange,
  id = "voice",
  className,
}: VoiceCaptureProps) {
  if (value) {
    return <VoicePreview value={value} onClear={() => onChange(null)} className={className} />;
  }

  const recordSupported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function" &&
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined";

  return (
    <Tabs defaultValue="preset" className={className} data-testid="voice-tabs">
      <TabsList aria-label="Voice input mode">
        <TabsTrigger value="preset" data-testid="voice-tab-preset">
          <Wand2 className="h-3 w-3" /> Preset
        </TabsTrigger>
        <TabsTrigger value="upload" data-testid="voice-tab-upload">
          <UploadCloud className="h-3 w-3" /> Upload
        </TabsTrigger>
        <TabsTrigger
          value="record"
          data-testid="voice-tab-record"
          disabled={!recordSupported}
          title={recordSupported ? undefined : "Recording isn't supported in this browser."}
        >
          <Mic className="h-3 w-3" /> Record
        </TabsTrigger>
      </TabsList>
      <TabsContent value="preset">
        <PresetPanel id={id} onChange={onChange} />
      </TabsContent>
      <TabsContent value="upload">
        <UploadDropzone id={id} onChange={onChange} />
      </TabsContent>
      <TabsContent value="record">
        {recordSupported ? (
          <RecordPanel onChange={onChange} />
        ) : (
          <VoiceMessage
            title="Recording isn't supported in this browser"
            body="Use the Upload tab to attach an audio file, or the Preset tab to pick a Runway voice."
            testId="record-unsupported"
          />
        )}
      </TabsContent>
    </Tabs>
  );
}

// ---- Preview (when value is set) -----------------------------------

function VoicePreview({
  value,
  onClear,
  className,
}: {
  value: VoiceCaptureValue;
  onClear: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-md border border-border bg-card/60 p-4",
        className,
      )}
      data-testid="voice-preview"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {describeMode(value)}
          </span>
          <span className="font-display text-lg leading-tight tracking-tight">
            {describeValue(value)}
          </span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClear}
          data-testid="voice-remove"
        >
          <X className="mr-1 h-3 w-3" /> Change
        </Button>
      </div>
      {value.mode !== "preset" && (
        <audio
          controls
          src={value.dataUri}
          className="w-full"
          data-testid="voice-preview-audio"
        />
      )}
    </div>
  );
}

function describeMode(value: VoiceCaptureValue): string {
  if (value.mode === "preset") return "Runway preset";
  if (value.mode === "upload") return "Uploaded clip";
  return "Recorded clip";
}

function describeValue(value: VoiceCaptureValue): string {
  if (value.mode === "preset") return value.preset;
  if (value.mode === "upload") return `${value.fileName} · ${formatBytes(value.bytes)}`;
  return `${formatDuration(value.durationMs)} · ${formatBytes(value.bytes)}`;
}

// ---- Preset tab -----------------------------------------------------

function PresetPanel({
  id,
  onChange,
}: {
  id: string;
  onChange: (value: VoiceCaptureValue) => void;
}) {
  const presets = useVoicePresets();
  const [selected, setSelected] = useState<string>("");

  if (presets.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading presets…</div>;
  }
  if (presets.isError || !presets.data) {
    return (
      <VoiceMessage
        title="Couldn't load presets"
        body="Refresh the page, or use the Upload / Record tab instead."
        testId="preset-error"
      />
    );
  }

  const submit = () => {
    if (!selected) return;
    onChange({ mode: "preset", preset: selected });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-preset`} className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
          Pick a Runway voice
        </Label>
        <select
          id={`${id}-preset`}
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="h-10 rounded-md border border-border bg-card px-3 font-mono text-sm capitalize transition-colors focus:border-primary focus:outline-none"
          data-testid="voice-preset-select"
        >
          <option value="">Choose…</option>
          {presets.data.map((p) => (
            <option key={p} value={p} className="capitalize">
              {p}
            </option>
          ))}
        </select>
      </div>
      <Button
        type="button"
        onClick={submit}
        disabled={!selected}
        data-testid="voice-preset-use"
      >
        Use this voice
      </Button>
    </div>
  );
}

// ---- Upload tab -----------------------------------------------------

function UploadDropzone({
  id,
  onChange,
  className,
}: {
  id: string;
  onChange: (value: VoiceCaptureValue) => void;
  className?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const accept = useCallback(
    async (file: File) => {
      setError(null);
      const mime = file.type || guessMimeFromName(file.name);
      if (!ACCEPTED_MIMES[mime]) {
        setError("Use mp3, wav, m4a, or webm.");
        return;
      }
      if (file.size > MAX_AUDIO_BYTES) {
        setError(`Too big — ${formatBytes(file.size)}. Max ${formatBytes(MAX_AUDIO_BYTES)}.`);
        return;
      }
      try {
        const dataUri = await readAsDataUri(file);
        onChange({
          mode: "upload",
          dataUri,
          fileName: file.name,
          bytes: file.size,
          mime,
        });
      } catch (exc) {
        setError(`Couldn't read the file (${(exc as Error).message}).`);
      }
    },
    [onChange],
  );

  const onSelect = useCallback(
    (ev: React.ChangeEvent<HTMLInputElement>) => {
      const file = ev.target.files?.[0];
      if (file) void accept(file);
      ev.target.value = "";
    },
    [accept],
  );

  const onDrop = useCallback(
    (ev: React.DragEvent<HTMLDivElement>) => {
      ev.preventDefault();
      setDragging(false);
      const file = ev.dataTransfer.files?.[0];
      if (file) void accept(file);
    },
    [accept],
  );

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-card/40 p-8 text-center transition-colors",
        "cursor-pointer hover:bg-card/70 focus-within:bg-card/70",
        dragging && "border-primary/60 bg-primary/5",
        className,
      )}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDrop={onDrop}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        e.preventDefault();
        setDragging(false);
      }}
      role="button"
      tabIndex={0}
      aria-label="Upload an audio clip"
      data-testid="voice-dropzone"
    >
      <UploadCloud className="h-6 w-6 text-muted-foreground" aria-hidden />
      <div className="flex flex-col gap-1">
        <span className="font-display text-lg leading-tight tracking-tight">
          Drop an audio clip here, or click to choose
        </span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          mp3 · wav · m4a · webm · max 15 MB · 10 s+ recommended
        </span>
      </div>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept="audio/mp3,audio/mpeg,audio/wav,audio/x-wav,audio/m4a,audio/mp4,audio/webm"
        className="sr-only"
        onChange={onSelect}
        data-testid="voice-input"
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

// ---- Record tab -----------------------------------------------------

type RecordState =
  | "idle"
  | "starting"
  | "ready"
  | "recording"
  | "captured"
  | "denied"
  | "unsupported"
  | "error";

function RecordPanel({
  onChange,
}: {
  onChange: (value: VoiceCaptureValue) => void;
}) {
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startedAtRef = useRef<number>(0);
  const timerRef = useRef<number | null>(null);

  const [state, setState] = useState<RecordState>("idle");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const [clip, setClip] = useState<{
    blob: Blob;
    objectUrl: string;
    durationMs: number;
  } | null>(null);

  const stopStream = useCallback(() => {
    const stream = streamRef.current;
    if (stream) stream.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Acquire mic + prep recorder on mount.
  useEffect(() => {
    let cancelled = false;

    async function start() {
      setState("starting");
      setErrorDetail(null);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true },
          video: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        setState("ready");
      } catch (exc) {
        if (cancelled) return;
        const err = exc as DOMException;
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          setState("denied");
        } else if (err.name === "NotFoundError" || err.name === "OverconstrainedError") {
          setState("unsupported");
        } else {
          setState("error");
          setErrorDetail(err.message || String(err));
        }
      }
    }

    void start();
    return () => {
      cancelled = true;
      stopStream();
      stopTimer();
      // Best-effort recorder cleanup. The MediaRecorder spec says
      // stop() on a stopped recorder is a no-op.
      try {
        recorderRef.current?.stop();
      } catch {
        // ignore
      }
    };
  }, [stopStream, stopTimer]);

  const beginRecording = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;
    chunksRef.current = [];

    // Pick a mime the browser supports. webm/opus is universal on
    // Chromium; Safari may need mp4 — we let the browser pick a
    // default if our preferred mime isn't supported.
    let mime = "audio/webm";
    if (typeof MediaRecorder.isTypeSupported === "function" &&
        !MediaRecorder.isTypeSupported(mime)) {
      mime = "audio/mp4";
      if (!MediaRecorder.isTypeSupported(mime)) {
        mime = ""; // let the UA decide
      }
    }

    let recorder: MediaRecorder;
    try {
      recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
    } catch (exc) {
      setState("error");
      setErrorDetail((exc as Error).message);
      return;
    }
    recorderRef.current = recorder;

    recorder.ondataavailable = (ev: BlobEvent) => {
      if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || "audio/webm",
      });
      const objectUrl = URL.createObjectURL(blob);
      const durationMs = Date.now() - startedAtRef.current;
      setClip({ blob, objectUrl, durationMs });
      setState("captured");
      stopTimer();
    };

    startedAtRef.current = Date.now();
    setElapsedMs(0);
    timerRef.current = window.setInterval(() => {
      const elapsed = Date.now() - startedAtRef.current;
      setElapsedMs(elapsed);
      if (elapsed >= MAX_RECORD_MS) {
        try {
          recorder.stop();
        } catch {
          // ignore
        }
      }
    }, 200);

    recorder.start();
    setState("recording");
  }, [stopTimer]);

  const endRecording = useCallback(() => {
    try {
      recorderRef.current?.stop();
    } catch {
      // ignore
    }
  }, []);

  const discardClip = useCallback(() => {
    if (clip) URL.revokeObjectURL(clip.objectUrl);
    setClip(null);
    setElapsedMs(0);
    setState(streamRef.current ? "ready" : "idle");
  }, [clip]);

  const useClip = useCallback(async () => {
    if (!clip) return;
    const dataUri = await blobToDataUri(clip.blob);
    onChange({
      mode: "record",
      dataUri,
      bytes: clip.blob.size,
      mime: clip.blob.type || "audio/webm",
      durationMs: clip.durationMs,
    });
  }, [clip, onChange]);

  if (state === "denied") {
    return (
      <VoiceMessage
        title="Microphone access blocked"
        body="Your browser blocked microphone access. Allow it in the site settings, or use the Upload tab instead."
        testId="record-denied"
      />
    );
  }
  if (state === "unsupported") {
    return (
      <VoiceMessage
        title="No microphone available"
        body="We couldn't find a working microphone on this device. Use the Upload tab instead."
        testId="record-unavailable"
      />
    );
  }
  if (state === "error") {
    return (
      <VoiceMessage
        title="Couldn't start the microphone"
        body={errorDetail ?? "Something went wrong while starting the microphone."}
        testId="record-error"
      />
    );
  }

  // Captured — preview + Use / Discard
  if (state === "captured" && clip) {
    const tooShort = clip.durationMs < MIN_RECORD_MS;
    return (
      <div className="flex flex-col gap-4" data-testid="record-captured">
        <audio
          controls
          src={clip.objectUrl}
          className="w-full"
          data-testid="record-playback"
        />
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {formatDuration(clip.durationMs)} · {formatBytes(clip.blob.size)}
            {tooShort && " · too short"}
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={discardClip}
              data-testid="record-discard"
            >
              <X className="mr-1 h-3 w-3" /> Discard
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={useClip}
              disabled={tooShort}
              title={tooShort ? `Record at least ${MIN_RECORD_MS / 1000}s — Runway needs it.` : undefined}
              data-testid="record-use"
            >
              <Play className="mr-1 h-3 w-3" /> Use clip
            </Button>
          </div>
        </div>
        {tooShort && (
          <p className="text-xs text-destructive">
            Runway needs at least {MIN_RECORD_MS / 1000} seconds of audio. Discard and re-record.
          </p>
        )}
      </div>
    );
  }

  // Idle / starting / ready / recording
  const startDisabled = state !== "ready";
  return (
    <div className="flex flex-col gap-4" data-testid="record-panel">
      <div className="flex flex-col items-center justify-center gap-3 rounded-md border border-dashed border-border bg-card/40 p-8 text-center">
        <Mic
          className={cn(
            "h-8 w-8",
            state === "recording" ? "text-destructive" : "text-muted-foreground",
          )}
          aria-hidden
        />
        <div className="flex flex-col gap-1">
          <span className="font-display text-lg leading-tight tracking-tight">
            {state === "starting" && "Connecting microphone…"}
            {state === "ready" && "Ready to record"}
            {state === "recording" && formatDuration(elapsedMs)}
            {state === "idle" && "Waiting for microphone"}
          </span>
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            10 s minimum · 5 min max · webm/opus
          </span>
        </div>
      </div>
      <div className="flex items-center justify-center gap-3">
        {state === "recording" ? (
          <Button
            type="button"
            size="lg"
            variant="destructive"
            onClick={endRecording}
            data-testid="record-stop"
          >
            <Square className="mr-1.5 h-4 w-4" /> Stop
          </Button>
        ) : (
          <Button
            type="button"
            size="lg"
            onClick={beginRecording}
            disabled={startDisabled}
            data-testid="record-start"
          >
            <Mic className="mr-1.5 h-4 w-4" />
            {state === "starting" ? "Starting…" : "Start recording"}
          </Button>
        )}
      </div>
    </div>
  );
}

// ---- Shared atoms ---------------------------------------------------

function VoiceMessage({
  title,
  body,
  testId,
}: {
  title: string;
  body: string;
  testId?: string;
}) {
  return (
    <div
      className="flex flex-col gap-2 rounded-md border border-dashed border-border bg-card/40 p-8 text-center"
      data-testid={testId}
    >
      <p className="font-display text-xl tracking-tight">{title}</p>
      <p className="mx-auto max-w-md text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

// ---- Helpers --------------------------------------------------------

function readAsDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === "string") resolve(result);
      else reject(new Error("FileReader returned non-string"));
    };
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(file);
  });
}

function blobToDataUri(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === "string") resolve(result);
      else reject(new Error("FileReader returned non-string"));
    };
    reader.onerror = () => reject(reader.error ?? new Error("blob read failed"));
    reader.readAsDataURL(blob);
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function formatDuration(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function guessMimeFromName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".mp3")) return "audio/mp3";
  if (lower.endsWith(".wav")) return "audio/wav";
  if (lower.endsWith(".m4a")) return "audio/m4a";
  if (lower.endsWith(".webm")) return "audio/webm";
  return "";
}
