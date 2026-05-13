/**
 * Lightweight fetch wrapper. The whole API surface goes through this.
 *
 * Responsibilities:
 *   - Same-origin credential mode (session cookies ride along).
 *   - CSRF: reads the `csrftoken` cookie and sets `X-CSRFToken` on
 *     non-GET requests to `/api/*` (Django's CSRF middleware is on).
 *     `allauth.headless` exempts its own routes via @csrf_exempt, so
 *     `/_allauth/*` requests don't need the header. We send it anyway
 *     when present — harmless either way.
 *   - JSON envelope: sets Content-Type for bodied requests, parses
 *     JSON responses.
 *   - Error normalisation: non-2xx responses throw `ApiError` with
 *     the parsed body attached.
 *
 * Per `docs/design/SPA_ARCHITECTURE.md` §"API client shape" and
 * §"Auth client shape".
 */

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]!) : null;
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function apiFetch(path: string, options: ApiFetchOptions = {}): Promise<Response> {
  const { body, headers: callerHeaders, ...rest } = options;
  const headers = new Headers(callerHeaders);

  const method = (options.method ?? "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    headers.set("Content-Type", "application/json");
    const csrf = readCookie("csrftoken");
    if (csrf) headers.set("X-CSRFToken", csrf);
  }

  const init: RequestInit = {
    ...rest,
    method,
    credentials: "same-origin",
    headers,
    body: body == null ? undefined : JSON.stringify(body),
  };

  return fetch(path, init);
}

/**
 * Helper for typed JSON GETs. The caller hands a zod parser so the
 * response shape is validated at the boundary, per the
 * SPA_ARCHITECTURE rule "zod at the API boundary."
 */
export async function apiJson<T>(
  path: string,
  options: ApiFetchOptions = {},
  parse?: (json: unknown) => T,
): Promise<T> {
  const resp = await apiFetch(path, options);
  const json = resp.status === 204 ? null : await resp.json().catch(() => null);

  if (!resp.ok) {
    throw new ApiError(`${options.method ?? "GET"} ${path} → ${resp.status}`, resp.status, json);
  }

  if (parse) return parse(json);
  return json as T;
}
