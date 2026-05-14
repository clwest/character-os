import { useState } from "react";
import { Camera, Sparkles, UploadCloud, Wand2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CameraCapture,
  UploadDropzone,
  type PortraitUploadResult,
} from "@/components/portrait-upload";
import {
  PORTRAIT_TEMPLATES,
  PORTRAIT_TEMPLATE_HINTS,
  PORTRAIT_TEMPLATE_LABELS,
  useGeneratePortrait,
  type PortraitTemplate,
} from "@/lib/api/spokespeople";
import { cn } from "@/lib/utils";

/**
 * Wizard Step 2 — Portrait (SESSION 130 — wizard slice 7).
 *
 * Three input modes via top-level tabs:
 *
 *   - **Upload** — drag-and-drop / file picker. Reuses
 *     `<UploadDropzone>` from `portrait-upload.tsx`.
 *   - **Camera** — `getUserMedia` capture. Reuses
 *     `<CameraCapture>` from the same module.
 *   - **Generate** — visual template + visual_subject + optional
 *     style → POST /api/spokespeople/generate-portrait/. Preview +
 *     Use / Regenerate. Powered by the SESSION 125
 *     /internal/portrait/ endpoint via the wrapper landed in
 *     SESSION 130.
 *
 * The chosen-portrait preview is shared across all three modes —
 * once a value is set, the operator sees one canonical preview +
 * a Change button that resets back to the tabbed input.
 *
 * The component takes a slim contract:
 *
 *   - ``value`` — current committed portrait (or null).
 *   - ``onChange`` — replace the committed portrait. The wizard's
 *     reducer maps this into SET_PORTRAIT.
 *   - ``onSubjectChange`` — when the operator types in the Generate
 *     tab's subject input, persist into the wizard's identity bag
 *     so it's still around if the operator switches back to Upload
 *     or Camera (and re-routes through Generate later).
 *   - ``initialSubject`` — pre-fill the Generate subject input
 *     (handy when the wizard already has a `visual_subject` from
 *     a prior pass through).
 */

interface WizardPortraitStepProps {
  value: PortraitUploadResult | null;
  onChange: (value: PortraitUploadResult | null) => void;
  onSubjectChange: (subject: string) => void;
  initialSubject?: string;
  className?: string;
}

export function WizardPortraitStep({
  value,
  onChange,
  onSubjectChange,
  initialSubject = "",
  className,
}: WizardPortraitStepProps) {
  if (value) {
    return (
      <PortraitPreview
        value={value}
        onClear={() => onChange(null)}
        className={className}
      />
    );
  }

  const cameraSupported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";

  return (
    <Tabs
      defaultValue="upload"
      className={className}
      data-testid="wizard-portrait-tabs"
    >
      <TabsList aria-label="Portrait input mode">
        <TabsTrigger value="upload" data-testid="wizard-portrait-tab-upload">
          <UploadCloud className="h-3 w-3" /> Upload
        </TabsTrigger>
        <TabsTrigger
          value="camera"
          data-testid="wizard-portrait-tab-camera"
          disabled={!cameraSupported}
          title={
            cameraSupported
              ? undefined
              : "Camera isn't supported in this browser."
          }
        >
          <Camera className="h-3 w-3" /> Take a picture
        </TabsTrigger>
        <TabsTrigger value="generate" data-testid="wizard-portrait-tab-generate">
          <Wand2 className="h-3 w-3" /> Generate
        </TabsTrigger>
      </TabsList>
      <TabsContent value="upload">
        <UploadDropzone id="wizard-portrait" onChange={onChange} />
      </TabsContent>
      <TabsContent value="camera">
        {cameraSupported ? (
          <CameraCapture onChange={onChange} />
        ) : (
          <div className="flex flex-col gap-2 rounded-md border border-dashed border-border bg-card/40 p-8 text-center">
            <p className="font-display text-xl tracking-tight">
              Camera isn't supported
            </p>
            <p className="mx-auto max-w-md text-sm text-muted-foreground">
              Use the Upload or Generate tab instead.
            </p>
          </div>
        )}
      </TabsContent>
      <TabsContent value="generate">
        <GeneratePanel
          onChange={onChange}
          onSubjectChange={onSubjectChange}
          initialSubject={initialSubject}
        />
      </TabsContent>
    </Tabs>
  );
}

// ---- Preview (shared across modes) ---------------------------------

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
    <div className={cn("flex items-start gap-4", className)} data-testid="wizard-portrait-preview">
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
          data-testid="wizard-portrait-change"
        >
          <X className="mr-1 h-3 w-3" /> Change
        </Button>
      </div>
    </div>
  );
}

// ---- Generate tab --------------------------------------------------

function GeneratePanel({
  onChange,
  onSubjectChange,
  initialSubject,
}: {
  onChange: (value: PortraitUploadResult) => void;
  onSubjectChange: (subject: string) => void;
  initialSubject: string;
}) {
  const [template, setTemplate] = useState<PortraitTemplate>("mascot");
  const [subject, setSubject] = useState(initialSubject);
  const [style, setStyle] = useState("");
  const generate = useGeneratePortrait();

  const submit = () => {
    // We don't auto-commit — the operator sees the preview +
    // Use/Regenerate CTAs and explicitly accepts. The preview
    // is held in `generate.data` (returned from useMutation).
    generate.mutate({
      template,
      subject: subject.trim() || undefined,
      style: style.trim() || undefined,
    });
  };

  const useIt = () => {
    if (!generate.data) return;
    onChange({
      dataUri: generate.data.portrait_data_uri,
      fileName: `generated-${generate.data.template}.png`,
      bytes: estimateBase64Bytes(generate.data.portrait_data_uri),
      mime: "image/png",
    });
    onSubjectChange(subject.trim());
    generate.reset();
  };

  return (
    <div className="flex flex-col gap-5" data-testid="wizard-portrait-generate">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[14rem,1fr]">
        <div className="flex flex-col gap-2">
          <Label
            htmlFor="wizard-portrait-template"
            className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            Visual template
          </Label>
          <select
            id="wizard-portrait-template"
            value={template}
            onChange={(e) => setTemplate(e.target.value as PortraitTemplate)}
            className="h-10 rounded-md border border-border bg-card px-3 font-mono text-sm transition-colors focus:border-primary focus:outline-none"
            data-testid="wizard-portrait-template-select"
          >
            {PORTRAIT_TEMPLATES.map((t) => (
              <option key={t} value={t}>
                {PORTRAIT_TEMPLATE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <p className="self-end text-xs text-muted-foreground">
          {PORTRAIT_TEMPLATE_HINTS[template]}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label
          htmlFor="wizard-portrait-subject"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Subject (optional)
        </Label>
        <p className="text-xs text-muted-foreground">
          Free-text "what they look like." Leave blank to use the
          template's built-in default ({" "}
          <span className="italic">{templateDefaultBlurb(template)}</span>{" "}
          ).
        </p>
        <Input
          id="wizard-portrait-subject"
          type="text"
          placeholder="armored battle unicorn warrior, neon-pink raccoon in a denim jacket…"
          maxLength={200}
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          data-testid="wizard-portrait-subject-input"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label
          htmlFor="wizard-portrait-style"
          className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
        >
          Style hint (optional)
        </Label>
        <Input
          id="wizard-portrait-style"
          type="text"
          placeholder="editorial illustration, oil-painting portrait, soft pastels…"
          maxLength={200}
          value={style}
          onChange={(e) => setStyle(e.target.value)}
          data-testid="wizard-portrait-style-input"
        />
      </div>

      {generate.data ? (
        <GeneratePreview
          dataUri={generate.data.portrait_data_uri}
          prompt={generate.data.prompt}
          mockMode={generate.data.mock_mode}
          onUse={useIt}
          onRegenerate={submit}
          pending={generate.isPending}
        />
      ) : (
        <Button
          type="button"
          onClick={submit}
          disabled={generate.isPending}
          data-testid="wizard-portrait-generate-submit"
        >
          <Sparkles className="mr-1.5 h-4 w-4" />
          {generate.isPending ? "Generating…" : "Generate portrait"}
        </Button>
      )}

      {generate.isError && (
        <p
          className="text-xs text-destructive"
          data-testid="wizard-portrait-generate-error"
        >
          Couldn't generate that portrait. Try a different template, simpler
          subject, or come back in a moment.
        </p>
      )}
    </div>
  );
}

function GeneratePreview({
  dataUri,
  prompt,
  mockMode,
  onUse,
  onRegenerate,
  pending,
}: {
  dataUri: string;
  prompt: string;
  mockMode: boolean;
  onUse: () => void;
  onRegenerate: () => void;
  pending: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-4 rounded-md border border-border bg-card/50 p-4"
      data-testid="wizard-portrait-generate-preview"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
        <div className="aspect-square w-40 overflow-hidden rounded-md border border-border bg-muted">
          <img src={dataUri} alt="" className="h-full w-full object-cover" />
        </div>
        <div className="flex flex-1 flex-col gap-2">
          <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            Preview {mockMode && "· mock-mode"}
          </span>
          <p className="line-clamp-4 text-xs leading-relaxed text-muted-foreground">
            {prompt}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRegenerate}
          disabled={pending}
          data-testid="wizard-portrait-regenerate"
        >
          {pending ? "Generating…" : "Regenerate"}
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={onUse}
          disabled={pending}
          data-testid="wizard-portrait-use"
        >
          Use this portrait
        </Button>
      </div>
    </div>
  );
}

// ---- Helpers --------------------------------------------------------

function templateDefaultBlurb(t: PortraitTemplate): string {
  switch (t) {
    case "mascot":
      return "a friendly brand mascot";
    case "founder":
      return "a polished founder spokesperson, mid-30s";
    case "coach":
      return "an energetic coach spokesperson, mid-30s";
    case "local_guide":
      return "a welcoming local-business spokesperson";
  }
}

function estimateBase64Bytes(dataUri: string): number {
  const i = dataUri.indexOf("base64,");
  if (i < 0) return 0;
  const payload = dataUri.slice(i + "base64,".length);
  return Math.ceil(payload.length * 0.75);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
