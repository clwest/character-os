import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const MAX_PORTRAIT_BYTES = 5 * 1024 * 1024; // 5 MB — matches backend cap
const ACCEPTED_MIMES: Record<string, true> = {
  "image/png": true,
  "image/jpeg": true,
  "image/webp": true,
};

export interface PortraitUploadResult {
  dataUri: string;
  fileName: string;
  bytes: number;
  mime: string;
}

interface PortraitUploadProps {
  value: PortraitUploadResult | null;
  onChange: (value: PortraitUploadResult | null) => void;
  id?: string;
  className?: string;
}

/**
 * Editorial portrait picker. Two input modes via tabs:
 *
 *   - **Upload** — drag-and-drop or click file picker. PNG/JPEG/WebP,
 *     5 MB cap.
 *   - **Camera** — in-browser capture via `getUserMedia`. Hidden
 *     entirely if `navigator.mediaDevices` is unsupported (older
 *     browsers, Safari in some embed contexts).
 *
 * Both paths produce the same `PortraitUploadResult` so consumers
 * don't branch on input mode. Lands the Browser-API foundation
 * the wizard's Step 2 + Step 3 audio capture inherit (per
 * `docs/design/CREATE_SPOKESPERSON_WIZARD.md` §"Camera + audio
 * capture").
 */
export function PortraitUpload({
  value,
  onChange,
  id = "portrait",
  className,
}: PortraitUploadProps) {
  // Show the preview-with-Remove when a value is set, regardless of
  // which tab produced it. After Remove → default back to Upload.
  if (value) {
    return <PortraitPreview value={value} onClear={() => onChange(null)} className={className} />;
  }

  const cameraSupported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";

  // When the camera isn't supported, skip the tabs UI entirely —
  // single-mode upload looks cleaner than a one-tab strip.
  if (!cameraSupported) {
    return <UploadDropzone id={id} onChange={onChange} className={className} />;
  }

  return (
    <Tabs defaultValue="upload" className={className} data-testid="portrait-tabs">
      <TabsList aria-label="Portrait input mode">
        <TabsTrigger value="upload" data-testid="portrait-tab-upload">
          <UploadCloud className="h-3 w-3" /> Upload
        </TabsTrigger>
        <TabsTrigger value="camera" data-testid="portrait-tab-camera">
          <Camera className="h-3 w-3" /> Take a picture
        </TabsTrigger>
      </TabsList>
      <TabsContent value="upload">
        <UploadDropzone id={id} onChange={onChange} />
      </TabsContent>
      <TabsContent value="camera">
        <CameraCapture onChange={onChange} />
      </TabsContent>
    </Tabs>
  );
}

// ---- Preview (when value is set) -----------------------------------

function PortraitPreview({
  value,
  onClear,
  className,
}: {
  value: PortraitUploadResult;
  onClear: () => void;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-4", className)}>
      <div className="aspect-square w-32 overflow-hidden rounded-md border border-border bg-muted">
        <img src={value.dataUri} alt="" className="h-full w-full object-cover" />
      </div>
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex flex-col gap-0.5">
          <span className="truncate font-display text-base leading-tight tracking-tight">
            {value.fileName}
          </span>
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {value.mime.replace("image/", "").toUpperCase()} · {formatBytes(value.bytes)}
          </span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onClear}
          className="self-start"
          data-testid="portrait-remove"
        >
          <X className="mr-1 h-3 w-3" /> Remove
        </Button>
      </div>
    </div>
  );
}

// ---- Upload tab (existing dropzone, extracted) ---------------------

function UploadDropzone({
  id,
  onChange,
  className,
}: {
  id: string;
  onChange: (value: PortraitUploadResult) => void;
  className?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const accept = useCallback(
    async (file: File) => {
      setError(null);
      if (!ACCEPTED_MIMES[file.type]) {
        setError("Use PNG, JPEG, or WebP.");
        return;
      }
      if (file.size > MAX_PORTRAIT_BYTES) {
        setError(`Too big — ${formatBytes(file.size)}. Max ${formatBytes(MAX_PORTRAIT_BYTES)}.`);
        return;
      }
      try {
        const dataUri = await readAsDataUri(file);
        onChange({
          dataUri,
          fileName: file.name,
          bytes: file.size,
          mime: file.type,
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
      aria-label="Upload a portrait"
      data-testid="portrait-dropzone"
    >
      <UploadCloud className="h-6 w-6 text-muted-foreground" aria-hidden />
      <div className="flex flex-col gap-1">
        <span className="font-display text-lg leading-tight tracking-tight">
          Drop a portrait here, or click to choose
        </span>
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          PNG · JPEG · WebP · max 5 MB · optional
        </span>
      </div>
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="sr-only"
        onChange={onSelect}
        data-testid="portrait-input"
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

// ---- Camera tab (new) ----------------------------------------------

type CameraState = "idle" | "starting" | "live" | "denied" | "unsupported" | "error";

function CameraCapture({
  onChange,
}: {
  onChange: (value: PortraitUploadResult) => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [state, setState] = useState<CameraState>("idle");
  const [errorDetail, setErrorDetail] = useState<string | null>(null);

  const stopStream = useCallback(() => {
    const stream = streamRef.current;
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
    }
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Start the stream when the component mounts. Re-runs are guarded
  // by streamRef — getUserMedia gets called once per mount lifecycle.
  useEffect(() => {
    let cancelled = false;

    async function start() {
      setState("starting");
      setErrorDetail(null);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 1024 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          // Play kicks off in React via the autoplay attribute, but
          // Safari sometimes needs an explicit play() after src set.
          videoRef.current.play().catch(() => {
            // Some browsers throw on programmatic play; harmless —
            // the video will start on its own.
          });
        }
        setState("live");
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
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1024;
    canvas.height = video.videoHeight || 1024;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUri = canvas.toDataURL("image/png");
    const bytes = Math.ceil((dataUri.length - "data:image/png;base64,".length) * 0.75);
    stopStream();
    onChange({
      dataUri,
      fileName: `camera-${Date.now()}.png`,
      bytes,
      mime: "image/png",
    });
  }, [onChange, stopStream]);

  if (state === "denied") {
    return (
      <CameraMessage
        title="Camera access blocked"
        body="Your browser blocked camera access. Allow it in the site settings, or upload a portrait file instead."
        testId="camera-denied"
      />
    );
  }
  if (state === "unsupported") {
    return (
      <CameraMessage
        title="No camera available"
        body="We couldn't find a working camera on this device. Use the Upload tab instead."
        testId="camera-unsupported"
      />
    );
  }
  if (state === "error") {
    return (
      <CameraMessage
        title="Couldn't start the camera"
        body={errorDetail ?? "Something went wrong while starting the camera."}
        testId="camera-error"
      />
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="camera-panel">
      <div className="overflow-hidden rounded-md border border-border bg-muted">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="aspect-square w-full bg-black object-cover"
          data-testid="camera-preview"
        />
      </div>
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          {state === "starting" ? "Starting camera…" : "Live · ready to capture"}
        </span>
        <Button
          type="button"
          size="lg"
          onClick={capture}
          disabled={state !== "live"}
          data-testid="camera-capture"
        >
          <Camera className="mr-1.5 h-4 w-4" />
          Take picture
        </Button>
      </div>
    </div>
  );
}

function CameraMessage({
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

// ---- Helpers -------------------------------------------------------

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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
