import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Standard shadcn helper. Combines clsx (conditional class strings)
// with tailwind-merge (deduplicates conflicting Tailwind classes so
// `cn("p-2", "p-4")` resolves to `p-4`).
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
