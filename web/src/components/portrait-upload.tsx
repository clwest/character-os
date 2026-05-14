import { useCallback, useRef, useState } from "react";
import { UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  /** Surface ID for the hidden file input — paired with <Label htmlFor>. */
  id?: string;
  className?: string;
}

/**
 * Editorial drag-and-drop / click upload. Returns a base64 data URI
 * so the SPA can POST it as `portrait_data_uri` to
 * `/api/spokespeople/` (SESSION 116 backend wiring).
 *
 * Validates mime + size client-side so the server doesn't see
 * obvious junk. Backend re-validates regardless.
 */
export function PortraitUpload({
  value,
  onChange,
  id = "portrait",
  className,
}: PortraitUploadProps) {
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
        setError(
          `Too big — ${formatBytes(file.size)}. Max ${formatBytes(MAX_PORTRAIT_BYTES)}.`,
        );
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
      ev.target.value = ""; // allow re-selecting the same file later
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

  const onDragOver = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setDragging(true);
  }, []);

  const onDragLeave = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setDragging(false);
  }, []);

  if (value) {
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
              {value.mime.replace("image/", "").toUpperCase()} ·{" "}
              {formatBytes(value.bytes)}
            </span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onChange(null)}
            className="self-start"
            data-testid="portrait-remove"
          >
            <X className="mr-1 h-3 w-3" /> Remove
          </Button>
        </div>
      </div>
    );
  }

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
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
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
