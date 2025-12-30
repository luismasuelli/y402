import { z } from "zod";
import { PaywallConfigSchema } from "./paywall";
import { HTTPInputSchema } from "./schema";
import { Y402Setup } from "./setup";


/**
 * Internal key used to attach endpoint settings.
 */
export const Y402_ENDPOINT_SETTINGS = "y402_endpoint_settings";


/**
 * The settings for a single endpoint. It also works as a decorator
 * to set the settings into a specific endpoint, which should return
 * a quick response based on the reference and nothing else, since
 * by its arrival the payment was already sent to the webhook.
 */
export const X402EndpointSettingsSchema = z.object({
    resourceUrl: z
        .string()
        .optional()
        .describe("An optional, normalized, resource URL for this endpoint"),

    referenceParam: z
        .string()
        .optional()
        .describe(
            "An optional field to tell which URL parameter stands for the internal reference. " +
            "Using references is like using tags in the way that they let to identify the payment " +
            "or the object / product / invoice being paid, but they are dynamic rather than static " +
            "(inferred from the URL). It is optional to use this, but once used it must match a " +
            "parameter from the URL. If not used, the reference will be an empty string for each " +
            "payment in this endpoint"
        ),

    description: z
        .string()
        .optional()
        .describe("An optional endpoint description"),

    maxDeadlineSeconds: z
        .number()
        .int()
        .optional()
        .describe(
            "An optional setting for the time this endpoint can wait for a given payment handshake. " +
            "If not set, then the default value can be configured in the middleware"
        ),

    inputSchema: HTTPInputSchema.optional().describe(
        "An optional input schema for the x402 response to hint the agents when using this endpoint"
    ),

    outputSchema: z
        .unknown()
        .optional()
        .describe(
            "An optional output schema for the x402 response to hint the agents when using this endpoint"
        ),

    mimeType: z
        .string()
        .default("")
        .describe("An optional MIME type for this endpoint"),

    paywallConfig: PaywallConfigSchema.optional().describe(
        "An optional paywall configuration (i.e. a coinbase developer platform app settings)"
    ),

    customPaywallHtml: z
        .string()
        .optional()
        .describe(
            "An optional HTML Paywall template for this endpoint in particular"
        ),

    customSetup: z
        .instanceof(Y402Setup)
        .optional()
        .describe(
            "A custom setup (i.e. to set more networks and more tokens) applying for this endpoint only. " +
            "It will merge to the setup in the middleware (only for this endpoint) to generate the " +
            "final layout of supported networks and tokens"
        ),

    tags: z
        .array(z.string())
        .optional()
        .describe("Arbitrary tags associated to this endpoint"),

    webhookName: z
        .string()
        .describe(
            "The webhook name. It is an arbitrary string. Dispatch workers must pick payments with " +
            "this value and batch-send them in order for any payment with this value to be sent " +
            "to the webhook"
        ),

    storageCollection: z
        .string()
        .describe("The collection to store the payments into for this endpoint"),
});


/**
 * The settings for a single endpoint. It also works as a decorator
 * to set the settings into a specific endpoint, which should return
 * a quick response based on the reference and nothing else, since
 * by its arrival the payment was already sent to the webhook.
 */
export type X402EndpointSettings = z.infer<typeof X402EndpointSettingsSchema>;


/**
 * attaches validated settings to an endpoint handler.
 *
 * Usage:
 *   const settings = createX402EndpointSettings({...});
 *   export const handler = withX402EndpointSettings(settings)(async (req,res)=>{...});
 */
export function withX402EndpointSettings(
    settings: X402EndpointSettings
) {
    return function <T extends Function>(endpoint: T): T {
        (endpoint as any)[Y402_ENDPOINT_SETTINGS] = settings;
        return endpoint;
    };
}

/**
 * Factory helper that validates and constructs settings using the schema.
 * (Optional convenience)
 */
export function createX402EndpointSettings(
    data: unknown
): X402EndpointSettings {
    return X402EndpointSettingsSchema.parse(data);
}
