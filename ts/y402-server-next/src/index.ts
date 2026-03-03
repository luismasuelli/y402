import {
    processPayment,
    server,
    DummyStorageManager,
    FinalEndpointSetupRegistry,
    FacilitatorConfigSchema,
    type FacilitatorConfig,
    type PaywallConfig,
    type PaymentPayload,
    type PaymentRequirements,
    type RequirePaymentDetails,
    type FinalRequiredPaymentDetails,
    type X402PaymentRequiredResponse,
    type Y402Setup,
    type StorageManager,
    type TokenAmount
} from "y402";
import { getRootUrl, resolveReferenceParam } from "./request_data";
import {
    Y402_ENDPOINT_SETTINGS,
    type X402EndpointSettings
} from "./types/endpoint_settings";

export type NextRouteContext = {
    params?: Record<string, string | string[]>;
};

export type NextRouteHandler = (
    request: Request,
    context: NextRouteContext
) => Response | Promise<Response>;

export type PaymentRequiredOptions = {
    mimeType?: string;
    defaultMaxDeadlineSeconds?: number;
    paywallConfig?: PaywallConfig;
    customPaywallHtml?: string;
    facilitatorConfig?: FacilitatorConfig;
    setup?: Y402Setup;
    storageManager?: StorageManager<PaymentPayload, PaymentRequirements>;
};

const X402_VERSION = 1;

function encodeBase64(input: string): string {
    if (typeof Buffer !== "undefined") {
        return Buffer.from(input, "utf-8").toString("base64");
    }
    if (typeof btoa !== "undefined") {
        return btoa(input);
    }
    throw new Error("No base64 encoder available");
}

function mapHeaders(headers: Headers): Record<string, unknown> {
    const mapped: Record<string, unknown> = {};
    headers.forEach((value, key) => {
        mapped[key] = value;
    });
    return mapped;
}

function basicPaywallHtml(error: string): string {
    return `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment Required</title></head>
  <body><h1>Payment Required</h1><p>${error}</p></body>
</html>`;
}

function makeResponseWithBody(
    response: Response,
    headers: Headers
): Response {
    return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers
    });
}

function paymentRequiredResponse(
    request: Request,
    statusCode: number,
    error: string,
    customPaywallHtml: string | undefined,
    paywallConfig: PaywallConfig | undefined,
    paymentRequirements: PaymentRequirements[],
    chainIdByName: Record<string, number>
): Response {
    void paywallConfig;
    const headers = new Headers();
    if (Object.keys(chainIdByName).length > 0) {
        headers.set("X-Payment-Networks", encodeBase64(JSON.stringify(chainIdByName)));
    }

    if (server.headers.isBrowserRequest(mapHeaders(request.headers))) {
        headers.set("Content-Type", "text/html; charset=utf-8");
        const html = customPaywallHtml || basicPaywallHtml(error);
        return new Response(html, { status: statusCode, headers });
    }

    const payload: X402PaymentRequiredResponse = {
        x402Version: X402_VERSION,
        accepts: paymentRequirements,
        error
    };

    headers.set("Content-Type", "application/json");
    return new Response(JSON.stringify(payload), { status: statusCode, headers });
}

function x402Response(
    request: Request,
    error: string,
    customPaywallHtml: string | undefined,
    paywallConfig: PaywallConfig | undefined,
    paymentRequirements: PaymentRequirements[],
    chainIdByName: Record<string, number>
): Response {
    return paymentRequiredResponse(
        request,
        402,
        error,
        customPaywallHtml,
        paywallConfig,
        paymentRequirements,
        chainIdByName
    );
}

async function computePrices(
    request: Request,
    paymentDetails: X402EndpointSettings["paymentDetails"],
    setup: Y402Setup
): Promise<FinalRequiredPaymentDetails[]> {
    const resolved = typeof paymentDetails === "function"
        ? await paymentDetails(request)
        : paymentDetails;
    return resolved.map((price: RequirePaymentDetails) => resolveFinalPayment(price, setup));
}

function isTokenAmount(value: unknown): value is TokenAmount {
    return typeof value === "object"
        && value !== null
        && "amount" in value
        && "asset" in value;
}

function resolveFinalPayment(
    requiredPayment: RequirePaymentDetails,
    setup: Y402Setup
): FinalRequiredPaymentDetails {
    const network = requiredPayment.network;
    const price = requiredPayment.price;

    if (typeof price === "string") {
        const [code, amount] = setup.parsePriceLabel(network, price);
        const [name, , address, version] = setup.getTokenMetadata(network, code);
        return {
            scheme: requiredPayment.scheme,
            network,
            payToAddress: requiredPayment.payToAddress,
            assetAddress: address,
            amountRequired: amount,
            eip712Domain: { name, version }
        };
    }

    if (typeof price === "number") {
        const code = setup.getDefaultToken(network);
        if (!code) {
            throw new Error(`The network ${network} does not have a default token`);
        }
        const [name, , address, version] = setup.getTokenMetadata(network, code);
        return {
            scheme: requiredPayment.scheme,
            network,
            payToAddress: requiredPayment.payToAddress,
            assetAddress: address,
            amountRequired: String(price),
            eip712Domain: { name, version }
        };
    }

    if (isTokenAmount(price)) {
        return {
            scheme: requiredPayment.scheme,
            network,
            payToAddress: requiredPayment.payToAddress,
            assetAddress: price.asset.address,
            amountRequired: price.amount,
            eip712Domain: {
                name: price.asset.eip712.name,
                version: price.asset.eip712.version
            }
        };
    }

    throw new Error(`Invalid price type: ${typeof price}`);
}

/**
 * Creates the y402 payment middleware.
 */
export function paymentRequired(
    endpoint: NextRouteHandler,
    options: PaymentRequiredOptions = {}
) {
    const {
        mimeType = "",
        defaultMaxDeadlineSeconds = 60,
        paywallConfig,
        customPaywallHtml,
        facilitatorConfig,
        setup,
        storageManager
    } = options;

    const registry = new FinalEndpointSetupRegistry(setup);
    const parsedFacilitatorConfig = FacilitatorConfigSchema.parse(facilitatorConfig ?? {});
    const storage = storageManager ?? new DummyStorageManager<PaymentPayload, PaymentRequirements>();

    return async function handler(
        request: Request,
        context: NextRouteContext = {}
    ): Promise<Response> {
        const endpointData = (endpoint as any)[Y402_ENDPOINT_SETTINGS] as X402EndpointSettings | undefined;
        if (!endpointData) {
            return await endpoint(request, context);
        }

        const resourceUrl = endpointData.resourceUrl
            ? `${getRootUrl(request)}/${endpointData.resourceUrl.replace(/^\/+/, "")}`
            : request.url;

        const description = endpointData.description || "";
        const maxDeadlineSeconds = endpointData.maxDeadlineSeconds || defaultMaxDeadlineSeconds;
        const mimeTypeValue = endpointData.mimeType || mimeType || "application/json";
        const outputSchema = endpointData.outputSchema;
        const inputSchema = endpointData.inputSchema;
        const paywallConfigValue = endpointData.paywallConfig || paywallConfig;
        const customPaywallHtmlValue = endpointData.customPaywallHtml || customPaywallHtml;
        const storageCollection = endpointData.storageCollection.trim() || "payments";

        let reference = "";
        if (endpointData.referenceParam) {
            const resolvedReference = resolveReferenceParam(context, endpointData.referenceParam);
            if (resolvedReference == null) {
                return paymentRequiredResponse(
                    request,
                    500,
                    `The resource ${resourceUrl} is not properly configured`,
                    customPaywallHtmlValue,
                    paywallConfigValue,
                    [],
                    {}
                );
            }
            reference = resolvedReference;
        }

        const mergedSetup = registry.get(endpoint as unknown as Function);
        const chainIdByName = mergedSetup.getChainIdsMapping();

        let prices: FinalRequiredPaymentDetails[];
        try {
            prices = await computePrices(request, endpointData.paymentDetails, mergedSetup);
        } catch {
            return paymentRequiredResponse(
                request,
                500,
                `The resource ${resourceUrl}'s setup / pricing is not properly configured`,
                customPaywallHtmlValue,
                paywallConfigValue,
                [],
                {}
            );
        }

        const paymentRequirements: PaymentRequirements[] = prices.map((price) => ({
            scheme: price.scheme,
            network: price.network,
            asset: price.assetAddress,
            maxAmountRequired: price.amountRequired,
            resource: resourceUrl,
            description,
            mimeType: mimeTypeValue,
            payTo: price.payToAddress,
            maxTimeoutSeconds: maxDeadlineSeconds,
            outputSchema: {
                input: {
                    type: "http",
                    method: request.method.toUpperCase(),
                    discoverable: true,
                    ...(inputSchema || {})
                },
                output: outputSchema
            },
            extra: price.eip712Domain
        }));

        const paymentHeader = request.headers.get("x-payment") || "";
        if (!paymentHeader) {
            return x402Response(
                request,
                "No X-PAYMENT header provided",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        let payment: PaymentPayload;
        try {
            payment = server.headers.decodePaymentHeader(paymentHeader);
        } catch {
            return x402Response(
                request,
                "Invalid payment header format",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        const paymentAssetHeader = (request.headers.get("x-payment-asset") || "").toLowerCase();
        const [, asset, ok] = server.headers.validatePaymentAsset(
            payment.network,
            payment,
            paymentAssetHeader,
            mergedSetup
        );
        if (!ok) {
            return x402Response(
                request,
                "Invalid payment asset",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        const requirement = paymentRequirements.find(
            (candidate) => candidate.asset === asset && candidate.network === payment.network
        );
        if (!requirement) {
            return x402Response(
                request,
                "Invalid payment asset",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        const invokeEndpoint = async (paymentId: string): Promise<[Response, boolean]> => {
            try {
                const response = await endpoint(request, context);
                return [response, response.status >= 200 && response.status < 400];
            } catch {
                const response = paymentRequiredResponse(
                    request,
                    500,
                    `An error occurred, but a payment was already processed. Contact support to claim your product or service by the internal payment id: ${paymentId}`,
                    customPaywallHtmlValue,
                    paywallConfigValue,
                    [],
                    chainIdByName
                );
                return [response, false];
            }
        };

        let settleResponse: any | null;
        let response: Response;
        try {
            [, settleResponse, response] = await processPayment(
                resourceUrl,
                endpointData.tags || [],
                reference,
                invokeEndpoint,
                payment,
                requirement,
                mergedSetup,
                parsedFacilitatorConfig,
                storage,
                storageCollection,
                endpointData.webhookName
            );
        } catch {
            return x402Response(
                request,
                "The payment was invalid or there was an error processing it",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        if (settleResponse && !settleResponse.success) {
            return x402Response(
                request,
                `Settle failed: ${settleResponse.errorReason || "Unknown error"}`,
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
        }

        const responseHeaders = new Headers(response.headers);
        if (settleResponse) {
            responseHeaders.set("X-PAYMENT-RESPONSE", encodeBase64(JSON.stringify(settleResponse)));
        }

        return makeResponseWithBody(response, responseHeaders);
    };
}

export * from "./types/endpoint_settings";
