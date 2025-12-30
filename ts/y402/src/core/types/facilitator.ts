import { z } from "zod";
import { X402_VERSION } from "./constants";
import { PaymentPayloadSchema } from "./client";
import { PaymentRequirementsSchema } from "./requirements";


/**
 * This class stands for a base request for the facilitator endpoints.
 */
export const BaseRequestSchema = z.object({
    x402Version: z
        .number()
        .int()
        .default(X402_VERSION)
        .describe(
            "The involved x402 version, for compatibility with the protocol"
        ),
    paymentPayload: PaymentPayloadSchema.describe("The client-sent payload"),
    paymentRequirements: PaymentRequirementsSchema.describe(
        "The allowed requirements for this payment"
    ),
});


/**
 * This class stands for a base request for the facilitator endpoints.
 */
export type BaseRequest = z.infer<typeof BaseRequestSchema>;


/**
 * Builds the JSON payload of this base request object.
 *
 * Returns:
 *   A dictionary with the JSON response.
 */
export function baseRequestToJson(req: BaseRequest) {
    return {
        x402Version: req.x402Version,
        paymentPayload: req.paymentPayload,
        paymentRequirements: req.paymentRequirements,
    };
}


/**
 * This class stands for the body a request to the /verify endpoint.
 */
export const VerifyRequestSchema = BaseRequestSchema;


/**
 * This class stands for the body a request to the /verify endpoint.
 */
export type VerifyRequest = BaseRequest;


/**
 * This class stands for the body of a /verify response.
 */
export const VerifyResponseSchema = z.object({
    isValid: z.boolean(),
    invalidReason: z.string().nullable().optional(),
    payer: z.string().optional(),
});


/**
 * This class stands for the body of a /verify response.
 */
export type VerifyResponse = z.infer<typeof VerifyResponseSchema>;


/**
 * This class stands for the body of a request to the /settle endpoint.
 */
export const SettleRequestSchema = BaseRequestSchema;


/**
 * This class stands for the body of a request to the /settle endpoint.
 */
export type SettleRequest = BaseRequest;


/**
 * This class stands for the body of a /settle response.
 */
export const SettleResponseSchema = z.object({
    success: z.boolean(),
    errorReason: z.string().nullable().optional(),
    transaction: z.string().optional(),
    network: z.string().optional(),
    payer: z.string().optional(),
});


/**
 * This class stands for the body of a /settle response.
 */
export type SettleResponse = z.infer<typeof SettleResponseSchema>;


/**
 * The way the headers are built when performing requests to
 * a x402 facilitator. They can be per endpoint and of types:
 *
 * 1. A dictionary.
 * 2. A callable returning a dictionary of headers.
 * 3. An awaitable callable returning a dictionary of headers.
 */
export type HeadersObject = Record<string, unknown>;
export type HeadersSyncFactory = () => HeadersObject;
export type HeadersAsyncFactory = () => Promise<HeadersObject>;

export type HeadersValue =
    | HeadersObject
    | HeadersSyncFactory
    | HeadersAsyncFactory;

export type FacilitatorHeaders = {
    settle?: HeadersValue;
    verify?: HeadersValue;
};

// Zod representation of the above types (Zod 4.2.1–compatible).
const HeadersObjectSchema = z.record(z.string(), z.unknown());

// We can't use z.function() in schemas in Zod 4.2.1, so we use z.custom.
const SyncHeadersFnSchema = z.custom<HeadersSyncFactory>(
    (val) => typeof val === "function",
    "Expected a sync headers factory function"
);

const AsyncHeadersFnSchema = z.custom<HeadersAsyncFactory>(
    (val) => typeof val === "function",
    "Expected an async headers factory function"
);

const HeadersValueSchema = z.union([
    HeadersObjectSchema,
    SyncHeadersFnSchema,
    AsyncHeadersFnSchema,
]);

export const FacilitatorHeadersSchema: z.ZodType<FacilitatorHeaders> =
    z.object({
        settle: HeadersValueSchema.optional(),
        verify: HeadersValueSchema.optional(),
    });

/**
 * Configuration for the X402 facilitator service.
 *
 * Attributes:
 *   url: The base URL for the facilitator service.
 *   headers: Optional function to create authentication headers.
 */
export const FacilitatorConfigSchema = z.object({
    url: z
        .string()
        .default("https://x402.org/facilitator")
        .describe(
            "The URL of the facilitator. It does not need to be a top-level URL but must " +
            "have two facilitator-compatible sub-endpoints named /verify and /settle"
        ),
    headers: FacilitatorHeadersSchema.optional().describe(
        "The headers, or header-generation callables, to generate the headers for each of the endpoints"
    ),
});


/**
 * Configuration for the X402 facilitator service.
 *
 * Attributes:
 *   url: The base URL for the facilitator service.
 *   headers: Optional function to create authentication headers.
 */
export type FacilitatorConfig = z.infer<typeof FacilitatorConfigSchema>;
