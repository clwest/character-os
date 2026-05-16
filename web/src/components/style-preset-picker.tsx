/**
 * Style preset picker — W11.6.3.
 *
 * Categorized gallery of the 42 Stability style presets surfaced
 * via ``GET /api/styles/`` (proxied from the media-engine's
 * ``style_library.py``). The picker is dumb display + selection;
 * the parent form owns the selected value.
 *
 * Contract rule 9 — every preset surfaces a short explanation
 * (display name + description + mood) so operators don't need to
 * know what "concept_art" looks like to pick it confidently.
 * Hover state surfaces ``best_for`` industries.
 *
 * Contract rule 10 — the 42 presets ARE the picker contract.
 * Removed presets must keep their slug in the library; new
 * presets land via media-engine code only, no SPA change.
 */
import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useStyleLibrary, type StylePreset } from "@/lib/api/images";

interface StylePresetPickerProps {
  value: string | undefined;
  onChange: (preset: string | undefined) => void;
  disabled?: boolean;
}

export function StylePresetPicker({
  value,
  onChange,
  disabled = false,
}: StylePresetPickerProps) {
  const library = useStyleLibrary();
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined);

  if (library.isLoading) {
    return (
      <div
        data-testid="style-preset-picker-loading"
        className="flex h-32 items-center justify-center gap-2 rounded-md border border-dashed border-border text-sm text-muted-foreground"
      >
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading style presets…
      </div>
    );
  }

  if (library.isError || !library.data) {
    return (
      <div
        data-testid="style-preset-picker-error"
        className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
      >
        Couldn't load the style library. Try again in a moment.
      </div>
    );
  }

  const categories = library.data.categories;
  const currentTab =
    activeTab ??
    categories.find((cat) => cat.presets.some((p) => p.name === value))?.id ??
    categories[0]?.id;

  if (!currentTab) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3" data-testid="style-preset-picker">
      <div className="flex items-center justify-between gap-2">
        <SelectionPill value={value} categories={categories} />
        {value && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onChange(undefined)}
            disabled={disabled}
            data-testid="style-preset-clear"
          >
            <X className="mr-1 h-3 w-3" />
            Clear
          </Button>
        )}
      </div>
      <Tabs
        value={currentTab}
        onValueChange={setActiveTab}
        className="flex flex-col gap-3"
      >
        <TabsList className="w-full flex-wrap justify-start gap-1 overflow-x-auto">
          {categories.map((cat) => (
            <TabsTrigger
              key={cat.id}
              value={cat.id}
              data-testid={`style-preset-tab-${cat.id}`}
              className="whitespace-nowrap"
            >
              <span aria-hidden className="mr-1">{cat.icon}</span>
              {cat.display_name}
            </TabsTrigger>
          ))}
        </TabsList>
        {categories.map((cat) => (
          <TabsContent
            key={cat.id}
            value={cat.id}
            className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3"
          >
            {cat.presets.map((preset) => (
              <PresetCard
                key={preset.name}
                preset={preset}
                selected={preset.name === value}
                disabled={disabled}
                onSelect={() => onChange(preset.name)}
              />
            ))}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

function SelectionPill({
  value,
  categories,
}: {
  value: string | undefined;
  categories: ReturnType<typeof useStyleLibrary>["data"] extends infer T
    ? T extends { categories: infer C }
      ? C
      : never
    : never;
}) {
  if (!value) {
    return (
      <span className="text-xs text-muted-foreground">
        No style preset selected — operator subject + purpose framing only.
      </span>
    );
  }
  const preset = categories
    ?.flatMap((c) => c.presets)
    .find((p) => p.name === value);
  if (!preset) {
    return (
      <span className="text-xs text-muted-foreground" data-testid="style-preset-selection">
        Selected: <strong>{value}</strong>
      </span>
    );
  }
  return (
    <span
      className="text-xs text-muted-foreground"
      data-testid="style-preset-selection"
    >
      Selected: <strong>{preset.display_name}</strong> · {preset.mood}
    </span>
  );
}

function PresetCard({
  preset,
  selected,
  disabled,
  onSelect,
}: {
  preset: StylePreset;
  selected: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      title={
        preset.best_for.length
          ? `Good for: ${preset.best_for.join(", ")}`
          : preset.description
      }
      data-testid={`style-preset-${preset.name}`}
      data-selected={selected ? "true" : "false"}
      className={cn(
        "flex flex-col gap-1 rounded-md border bg-card p-3 text-left transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected
          ? "border-foreground bg-foreground/5"
          : "border-border hover:border-foreground/30",
        disabled && "opacity-60",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{preset.display_name}</span>
        <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          {preset.mood}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{preset.description}</p>
    </button>
  );
}
