/**
 * Recipe gallery — SPA entry point for video creation.
 *
 * V15.1-V15.4 turned this into the 18-card live gallery.
 * F1 (workspace fabric arc) adds the `?spokesperson=<id>`
 * URL hint: when present, every card link propagates the
 * hint to the recipe form so the spokesperson dropdown
 * comes pre-bound. Per F0 contract rule 2 the hint is
 * never a binding — the form still lets operators change
 * the selection.
 */
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Lock, Sparkles, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  LIVE_RECIPE_KINDS,
  RECIPE_FAMILIES,
  RECIPE_FAMILY_LABELS,
  type Recipe,
  type RecipeFamily,
  useRecipes,
} from "@/lib/api/recipes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { SectionHeader } from "@/components/editorial";

export function RecipeGalleryRoute() {
  const recipes = useRecipes();
  const [searchParams] = useSearchParams();
  const spokespersonHint = searchParams.get("spokesperson") ?? undefined;
  // SESSION 262 — Episode context propagates through the gallery to
  // whichever recipe the operator picks. Same pattern as
  // spokespersonHint above; the recipe form reads `?episode=` and
  // attaches the resulting Composition to that Episode on submit.
  const episodeHint = searchParams.get("episode") ?? undefined;
  const spokespeople = useSpokespeople();
  const hintedSpokesperson = spokespersonHint
    ? spokespeople.data?.find((s) => s.id === spokespersonHint)
    : undefined;

  return (
    <div className="flex flex-col gap-8 py-10">
      <Header hintedSpokespersonName={hintedSpokesperson?.name} />
      {recipes.isLoading && <GallerySkeleton />}
      {recipes.isError && (
        <ErrorState message={extractMessage(recipes.error)} />
      )}
      {recipes.data && (
        <RecipeGrid
          recipes={recipes.data}
          spokespersonHint={spokespersonHint}
          episodeHint={episodeHint}
        />
      )}
    </div>
  );
}

function Header({ hintedSpokespersonName }: { hintedSpokespersonName?: string }) {
  return (
    <header className="relative flex flex-col gap-4 pb-10">
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
      >
        <ArrowLeft className="h-3 w-3" />
        Back to dashboard
      </Link>
      <div className="flex flex-col gap-3">
        <SectionHeader number={3} title="Recipe Gallery" />
        <h1 className="font-display text-4xl leading-tight tracking-tight text-cream md:text-5xl">
          {hintedSpokespersonName
            ? `What can ${hintedSpokespersonName} produce?`
            : <>Pick a <span className="italic gold-text">composition</span> recipe.</>}
        </h1>
        <p className="max-w-2xl text-base text-mist">
          Each card is a starter composition — a prebuilt step sequence the
          render pipeline executes against the media engine. Pick one, fill
          in the parameters, and the composition runs against your workspace
          knowledge + the selected spokesperson.
        </p>
        {hintedSpokespersonName && (
          <div
            className="mt-1 inline-flex w-fit items-center gap-2 rounded-full border border-luxe bg-card/60 px-3 py-1 text-xs"
            data-testid="spokesperson-hint-chip"
          >
            <User className="h-3 w-3 text-fog" />
            <span className="text-mist">
              Pre-bound to <strong className="text-cream">{hintedSpokespersonName}</strong>
            </span>
            <Link
              to="/recipes"
              className="ml-1 font-mono text-[10px] uppercase tracking-[0.22em] text-fog transition-colors hover:text-gold"
              data-testid="spokesperson-hint-clear"
            >
              clear
            </Link>
          </div>
        )}
      </div>
      <div
        className="hairline-gold absolute inset-x-0 bottom-0 h-px"
        aria-hidden="true"
      />
    </header>
  );
}

function RecipeGrid({
  recipes,
  spokespersonHint,
  episodeHint,
}: {
  recipes: Recipe[];
  spokespersonHint?: string;
  episodeHint?: string;
}) {
  const byFamily = groupByFamily(recipes);

  return (
    <div className="flex flex-col gap-12">
      {RECIPE_FAMILIES.map((family) => {
        const list = byFamily.get(family) ?? [];
        if (list.length === 0) return null;
        return (
          <section key={family} className="flex flex-col gap-4">
            <FamilyHeading family={family} count={list.length} />
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {list.map((recipe) => (
                <RecipeCard
                  key={recipe.kind}
                  recipe={recipe}
                  spokespersonHint={spokespersonHint}
                  episodeHint={episodeHint}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function FamilyHeading({
  family,
  count,
}: {
  family: RecipeFamily;
  count: number;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-luxe pb-2">
      <h2 className="font-display text-xl tracking-tight text-cream">
        {RECIPE_FAMILY_LABELS[family]}
      </h2>
      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
        {count} {count === 1 ? "recipe" : "recipes"}
      </span>
    </div>
  );
}

function RecipeCard({
  recipe,
  spokespersonHint,
  episodeHint,
}: {
  recipe: Recipe;
  spokespersonHint?: string;
  episodeHint?: string;
}) {
  const isLive = LIVE_RECIPE_KINDS.has(recipe.kind);
  const params = new URLSearchParams();
  if (spokespersonHint) params.set("spokesperson", spokespersonHint);
  if (episodeHint) params.set("episode", episodeHint);
  const qs = params.toString();
  const href = qs
    ? `/recipes/${recipe.kind}?${qs}`
    : `/recipes/${recipe.kind}`;

  return (
    <Link
      to={href}
      data-testid={`recipe-card-${recipe.kind}`}
      data-live={isLive ? "true" : "false"}
      className={
        "group flex flex-col gap-3 rounded-md border border-luxe bg-card p-5 luxe-shadow transition " +
        (isLive
          ? "hover:border-gold/40"
          : "opacity-75 hover:opacity-100")
      }
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-lg leading-tight tracking-tight text-cream">
          {recipe.display_name}
        </h3>
        {isLive ? (
          <Sparkles
            className="h-4 w-4 text-fog transition group-hover:text-gold"
            aria-label="Available now"
          />
        ) : (
          <Lock
            className="h-4 w-4 text-fog"
            aria-label="Coming soon"
          />
        )}
      </div>
      <p className="text-sm text-mist">{recipe.description}</p>
      <div className="mt-auto flex items-center justify-between border-t border-luxe pt-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
          {recipe.fields.length} {recipe.fields.length === 1 ? "field" : "fields"}
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-fog">
          {isLive ? "Available →" : "Coming soon"}
        </span>
      </div>
    </Link>
  );
}

function GallerySkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="flex h-48 animate-pulse flex-col gap-3 rounded-md border bg-card p-5"
        >
          <div className="h-5 w-3/4 rounded bg-muted" />
          <div className="h-3 w-full rounded bg-muted" />
          <div className="h-3 w-5/6 rounded bg-muted" />
        </div>
      ))}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-5 text-sm">
      <p>Couldn't load recipes: {message}</p>
      <Button asChild variant="outline" size="sm">
        <Link to="/dashboard">Back to dashboard</Link>
      </Button>
    </div>
  );
}

function groupByFamily(recipes: Recipe[]): Map<RecipeFamily, Recipe[]> {
  const map = new Map<RecipeFamily, Recipe[]>();
  for (const recipe of recipes) {
    const list = map.get(recipe.family) ?? [];
    list.push(recipe);
    map.set(recipe.family, list);
  }
  return map;
}

function extractMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Unknown error";
}
