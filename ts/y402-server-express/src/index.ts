import type { Request, Response, NextFunction, RequestHandler } from "express";
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
import { getRootUrl } from "./request_data";
import {
    Y402_ENDPOINT_SETTINGS,
    type X402EndpointSettings
} from "./types/endpoint_settings";

export type ExpressEndpointHandler = (req: Request, res: Response) => void | Promise<void>;

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

function basicPaywallHtml(error: string): string {
    return `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment Required</title></head>
  <body><h1>Payment Required</h1><p>${error}</p></body>
</html>`;
}

function paymentRequiredResponse(
    request: Request,
    statusCode: number,
    error: string,
    customPaywallHtml: string | undefined,
    paywallConfig: PaywallConfig | undefined,
    paymentRequirements: PaymentRequirements[],
    chainIdByName: Record<string, number>
): { status: number; body: string; headers: Record<string, string> } {
    void paywallConfig;
    const encodedNetworks = Object.keys(chainIdByName).length > 0
        ? encodeBase64(JSON.stringify(chainIdByName))
        : null;

    const headers: Record<string, string> = {};
    if (encodedNetworks) {
        headers["X-Payment-Networks"] = encodedNetworks;
    }

    if (server.headers.isBrowserRequest(request.headers as Record<string, unknown>)) {
        headers["Content-Type"] = "text/html; charset=utf-8";
        return {
            status: statusCode,
            body: customPaywallHtml || basicPaywallHtml(error),
            headers
        };
    }

    headers["Content-Type"] = "application/json";
    const payload: X402PaymentRequiredResponse = {
        x402Version: X402_VERSION,
        accepts: paymentRequirements,
        error
    };
    return {
        status: statusCode,
        body: JSON.stringify(payload),
        headers
    };
}

function x402Response(
    request: Request,
    error: string,
    customPaywallHtml: string | undefined,
    paywallConfig: PaywallConfig | undefined,
    paymentRequirements: PaymentRequirements[],
    chainIdByName: Record<string, number>
): { status: number; body: string; headers: Record<string, string> } {
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
 * Creates an Express middleware-equivalent wrapper for one endpoint.
 * @param endpoint The endpoint to wrap.
 * @param options Optional middleware-level settings.
 * @returns The wrapped Express handler.
 */
export function paymentRequired(
    endpoint: ExpressEndpointHandler,
    options: PaymentRequiredOptions = {}
): RequestHandler {
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

    return async function wrappedEndpoint(req: Request, res: Response, _: NextFunction): Promise<void> {
        void _;
        const endpointData = (endpoint as any)[Y402_ENDPOINT_SETTINGS] as X402EndpointSettings | undefined;
        if (!endpointData) {
            await endpoint(req, res);
            return;
        }

        const resourceUrl = endpointData.resourceUrl
            ? `${getRootUrl(req)}/${endpointData.resourceUrl.replace(/^\/+/, "")}`
            : `${getRootUrl(req)}${req.originalUrl}`;

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
            const value = req.params?.[endpointData.referenceParam];
            if (typeof value !== "string") {
                const error = paymentRequiredResponse(
                    req,
                    500,
                    `The resource ${resourceUrl} is not properly configured`,
                    customPaywallHtmlValue,
                    paywallConfigValue,
                    [],
                    {}
                );
                res.status(error.status).set(error.headers).send(error.body);
                return;
            }
            reference = value;
        }

        const mergedSetup = registry.get(endpoint as unknown as Function);
        const chainIdByName = mergedSetup.getChainIdsMapping();

        let prices: FinalRequiredPaymentDetails[];
        try {
            prices = await computePrices(req, endpointData.paymentDetails, mergedSetup);
        } catch {
            const error = paymentRequiredResponse(
                req,
                500,
                `The resource ${resourceUrl}'s setup / pricing is not properly configured`,
                customPaywallHtmlValue,
                paywallConfigValue,
                [],
                {}
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
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
                    method: req.method.toUpperCase(),
                    discoverable: true,
                    ...(inputSchema || {})
                },
                output: outputSchema
            },
            extra: price.eip712Domain
        }));

        const paymentHeader = req.header("X-PAYMENT") || "";
        if (!paymentHeader) {
            const error = x402Response(
                req,
                "No X-PAYMENT header provided",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        let payment: PaymentPayload;
        try {
            payment = server.headers.decodePaymentHeader(paymentHeader);
        } catch {
            const error = x402Response(
                req,
                "Invalid payment header format",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        const paymentAssetHeader = (req.header("X-PAYMENT-ASSET") || "").toLowerCase();
        const [, asset, ok] = server.headers.validatePaymentAsset(
            payment.network,
            payment,
            paymentAssetHeader,
            mergedSetup
        );
        if (!ok) {
            const error = x402Response(
                req,
                "Invalid payment asset",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        const requirement = paymentRequirements.find(
            (candidate) => candidate.asset === asset && candidate.network === payment.network
        );
        if (!requirement) {
            const error = x402Response(
                req,
                "Invalid payment asset",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        let endpointSucceeded = false;

        const invokeEndpoint = async (paymentId: string): Promise<[Response, boolean]> => {
            try {
                await endpoint(req, res);
                endpointSucceeded = res.statusCode >= 200 && res.statusCode < 400;
                return [res, endpointSucceeded];
            } catch {
                const error = paymentRequiredResponse(
                    req,
                    500,
                    `An error occurred, but a payment was already processed. Contact support to claim your product or service by the internal payment id: ${paymentId}`,
                    customPaywallHtmlValue,
                    paywallConfigValue,
                    [],
                    chainIdByName
                );
                res.status(error.status).set(error.headers).send(error.body);
                endpointSucceeded = false;
                return [res, false];
            }
        };

        let settleResponse: any | null = null;
        try {
            const [, settle, ] = await processPayment(
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
            settleResponse = settle;
        } catch {
            const error = x402Response(
                req,
                "The payment was invalid or it was an error processing it",
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        if (settleResponse && !settleResponse.success) {
            const error = x402Response(
                req,
                `Settle failed: ${settleResponse.errorReason || "Unknown error"}`,
                customPaywallHtmlValue,
                paywallConfigValue,
                paymentRequirements,
                chainIdByName
            );
            res.status(error.status).set(error.headers).send(error.body);
            return;
        }

        if (settleResponse && endpointSucceeded) {
            res.set("X-PAYMENT-RESPONSE", encodeBase64(JSON.stringify(settleResponse)));
        }
    };
}

export * from "./types/endpoint_settings";
