import {
    VerifyRequest,
    VerifyResponse, VerifyResponseSchema,
    SettleRequest,
    SettleResponse, SettleResponseSchema,
    FacilitatorConfig, FacilitatorConfigSchema,
} from "../core/types/facilitator";
import {
    VerifyFacilitatorInvalidError,
    VerifyBadResponse,
    SettleBadResponse,
    SettleFacilitatorFailedError,
    VerifyFacilitatorUnknownError, SettleFacilitatorUnknownError,
} from "./errors";
import { makeHeaders } from "./utils";
import { BaseError, ConditionalDependencyError } from "../core/types/errors";


type Endpoint = "verify" | "settle";


/**
 * A fetch-based facilitator client.
 */
export class FacilitatorClient {
    protected readonly config: FacilitatorConfig;

    constructor(config?: FacilitatorConfig) {
        this.config = config ?? FacilitatorConfigSchema.parse({});
    }

    protected makeHeaders(endpoint: Endpoint): Record<string, string> {
        return makeHeaders(this.config.headers ?? {}, endpoint);
    }

    private ensureFetchAvailable(): void {
        if (typeof fetch === "undefined") {
            throw new ConditionalDependencyError(
                "fetch is not available in this environment. Provide a global fetch implementation (e.g. node-fetch or undici).",
            );
        }
    }

    private async fetchWithTimeout(
        url: string,
        timeoutSeconds: number,
        init: RequestInit,
    ): Promise<Response> {
        const timeoutMs = Math.max(1, timeoutSeconds) * 1000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            return await fetch(url, {
                ...init,
                signal: controller.signal,
            });
        } finally {
            clearTimeout(timeoutId);
        }
    }

    protected checkVerifyStatus(
        statusCode: number,
        content: Uint8Array,
        contentType: string,
    ): void {
        if (statusCode < 200 || statusCode >= 300) {
            throw new VerifyBadResponse(statusCode, content, contentType);
        }
    }

    protected parseVerifyObj(obj: Record<string, unknown>): VerifyResponse {
        const parsed = new VerifyResponseSchema.parse(obj);
        if (!parsed.isValid) {
            throw new VerifyFacilitatorInvalidError(parsed);
        }
        return parsed;
    }

    /**
     * Sends a verification request to the facilitator. Raises on timeout or bad status.
     * @param request The request to send.
     * @param timeout The timeout we'll tolerate.
     * @returns The response (async function).
     */
    async verify(
        request: VerifyRequest,
        timeout = 10,
    ): Promise<VerifyResponse> {
        this.ensureFetchAvailable();

        const headers = this.makeHeaders("verify");
        const url = `${this.config.url.replace(/\/+$/, "")}/verify`;

        const payload =
            typeof (request as any).toJSON === "function"
                ? (request as any).toJSON()
                : typeof (request as any).to_json === "function"
                    ? (request as any).to_json()
                    : (request as unknown as Record<string, unknown>);

        try {
            const response = await this.fetchWithTimeout(url, timeout, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...headers,
                },
                body: JSON.stringify(payload),
            });

            const cloned = response.clone();
            const contentType = response.headers.get("content-type") ?? "";
            const buffer = await response.arrayBuffer();
            const content = new Uint8Array(buffer);

            this.checkVerifyStatus(response.status, content, contentType);

            const json = (await cloned.json()) as Record<string, unknown>;
            return this.parseVerifyObj(json);
        } catch (err) {
            if (err instanceof BaseError) {
                throw err;
            }
            throw new VerifyFacilitatorUnknownError(err as Error);
        }
    }

    protected checkSettleStatus(
        statusCode: number,
        content: Uint8Array,
        contentType: string,
    ): void {
        if (statusCode < 200 || statusCode >= 300) {
            throw new SettleBadResponse(statusCode, content, contentType);
        }
    }

    protected parseSettleObj(obj: Record<string, unknown>): SettleResponse {
        const parsed = new SettleResponseSchema.parse(obj);
        if (!parsed.success) {
            throw new SettleFacilitatorFailedError(parsed);
        }
        return parsed;
    }

    /**
     * Sends a settle request to the facilitator. Raises on timeout or bad status.
     * @param request The request to send.
     * @param timeout The timeout we'll tolerate.
     * @returns The response (async function).
     */
    async settle(
        request: SettleRequest,
        timeout = 10,
    ): Promise<SettleResponse> {
        this.ensureFetchAvailable();

        const headers = this.makeHeaders("settle");
        const url = `${this.config.url.replace(/\/+$/, "")}/settle`;

        const payload =
            typeof (request as any).toJSON === "function"
                ? (request as any).toJSON()
                : typeof (request as any).to_json === "function"
                    ? (request as any).to_json()
                    : (request as unknown as Record<string, unknown>);

        try {
            const response = await this.fetchWithTimeout(url, timeout, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...headers,
                },
                body: JSON.stringify(payload),
            });

            const cloned = response.clone();
            const contentType = response.headers.get("content-type") ?? "";
            const buffer = await response.arrayBuffer();
            const content = new Uint8Array(buffer);

            this.checkSettleStatus(response.status, content, contentType);

            const json = (await cloned.json()) as Record<string, unknown>;
            return this.parseSettleObj(json);
        } catch (err) {
            if (err instanceof BaseError) {
                throw err;
            }
            throw new SettleFacilitatorUnknownError(err as Error);
        }
    }
}
