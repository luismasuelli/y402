import { Request } from "express";

/**
 * Retrieves the root URL (i.e. no path nor trailing slash).
 * @param request The current request.
 * @returns The base proto://host URL.
 */
export function getRootUrl(request: Request): string {
    const scheme = (request.headers["x-forwarded-proto"] as string) || request.protocol;
    const host = (request.headers["x-forwarded-host"] as string)
        || request.headers.host
        || request.get("host")
        || request.hostname;
    return `${scheme}://${host}`;
}
