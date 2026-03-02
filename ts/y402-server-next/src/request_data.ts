import type { NextRouteContext } from "./index";

/**
 * Retrieves the root URL (i.e. no path nor trailing slash).
 * @param request The current request.
 * @returns The base proto://host URL.
 */
export function getRootUrl(request: Request): string {
    const forwardedProto = request.headers.get("x-forwarded-proto");
    const scheme = forwardedProto || new URL(request.url).protocol.replace(":", "");
    const host = request.headers.get("x-forwarded-host")
        || request.headers.get("host")
        || new URL(request.url).host;
    return `${scheme}://${host}`;
}

/**
 * Resolves one reference parameter from route context.
 * @param context The Next route context.
 * @param paramName The parameter name to read.
 * @returns A string value if present, else null.
 */
export function resolveReferenceParam(
    context: NextRouteContext,
    paramName: string
): string | null {
    const value = context.params?.[paramName];
    if (typeof value === "string") {
        return value;
    }
    if (Array.isArray(value) && value.length > 0) {
        return value[0] ?? null;
    }
    return null;
}
