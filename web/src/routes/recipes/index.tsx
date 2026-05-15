/**
 * Recipe gallery — the V15 SPA entry point for video creation.
 *
 * Lists all 17 starter compositions as cards grouped by family.
 * V15.1 has three live recipes (talking_head, cinematic_visual,
 * talking_head_polished); the rest are "coming soon" cards that
 * preview the gallery shape. Forms land family-by-family in
 * V15.2-V15.4.
 */
import { Link } from "react-router-dom";
import { ArrowLeft, Lock, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  LIVE_RECIPE_KINDS,
  RECIPE_FAMILIES,
  RECIPE_FAMILY_LABELS,
  type Recipe,
  type RecipeFamily,
  useRecipes,
} from "@/lib/api/recipes";

export function RecipeGalleryRoute() {
  const recipes = useRecipes();

  return (
    <div className="flex flex-col gap-8 py-10">
      <Header />
      {recipes.isLoading && <GallerySkeleton />}
      {recipes.isError && (
        <ErrorState message={extractMessage(recipes.error)} />
      )}
      {recipes.data && <RecipeGrid recipes={recipes.data} />}
    </div>
  );
}

function Header() {
  return (
    <header className="flex flex-col gap-3">
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        Back to dashboard
      </Link>
      <div className="flex flex-col gap-2">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Make a video
        </span>
        <h1 className="font-display text-4xl leading-tight tracking-tight">
          Pick a recipe.
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Each card is a starter composition — a prebuilt sequence of steps the
          render engine knows how to run. Pick one, fill in the form, and the
          composition runs against the media engine.
        </p>
      </div>
    </header>
  );
}

function RecipeGrid({ recipes }: { recipes: Recipe[] }) {
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
                <RecipeCard key={recipe.kind} recipe={recipe} />
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
    <div className="flex items-baseline justify-between border-b pb-2">
      <h2 className="font-display text-xl tracking-tight">
        {RECIPE_FAMILY_LABELS[family]}
      </h2>
      <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
        {count} {count === 1 ? "recipe" : "recipes"}
      </span>
    </div>
  );
}

function RecipeCard({ recipe }: { recipe: Recipe }) {
  const isLive = LIVE_RECIPE_KINDS.has(recipe.kind);

  return (
    <Link
      to={`/recipes/${recipe.kind}`}
      data-testid={`recipe-card-${recipe.kind}`}
      data-live={isLive ? "true" : "false"}
      className={
        "group flex flex-col gap-3 rounded-md border bg-card p-5 shadow-paper transition " +
        (isLive
          ? "hover:border-foreground hover:shadow-paper-hover"
          : "opacity-75 hover:opacity-100")
      }
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-lg leading-tight tracking-tight">
          {recipe.display_name}
        </h3>
        {isLive ? (
          <Sparkles
            className="h-4 w-4 text-foreground/60 transition group-hover:text-foreground"
            aria-label="Available now"
          />
        ) : (
          <Lock
            className="h-4 w-4 text-muted-foreground"
            aria-label="Coming soon"
          />
        )}
      </div>
      <p className="text-sm text-muted-foreground">{recipe.description}</p>
      <div className="mt-auto flex items-center justify-between border-t pt-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          {recipe.fields.length} {recipe.fields.length === 1 ? "field" : "fields"}
        </span>
        <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          {isLive ? "Available" : "Coming soon"}
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
