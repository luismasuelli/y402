import { FacilitatorHeaders } from "../core/types/facilitator";
import { HeadersBuildingFacilitatorError } from "./errors";


type Endpoint = "settle" | "verify";


/**
 * Builds / fixes the effective headers for an endpoint.
 * @param headers The headers spec (both for settle and verify).
 * @param endpoint The endpoint to build headers for.
 */
export function makeHeaders(
    headers: FacilitatorHeaders,
    endpoint: Endpoint,
): Record<string, string> {
    const spec = headers?.[endpoint];

    if (!spec) {
        return {};
    }

    // If it's already a plain object, return as-is
    if (typeof spec === "object" && !Array.isArray(spec)) {
        return spec as Record<string, string>;
    }

    // Otherwise, treat it as a callable
    try {
        return (spec as () => Record<string, string>)();
    } catch (err) {
        throw new HeadersBuildingFacilitatorError(err as Error);
    }
}
