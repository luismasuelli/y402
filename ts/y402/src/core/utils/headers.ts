import { toByteArray } from "base64-js";
import { PaymentPayloadSchema, type PaymentPayload } from "../types/client";
import { Y402Setup } from "../types/setup";
import { checkSignature } from "./signature";


/**
 * Determine if request is from a browser vs API client.
 *
 * Args:
 *   headers: Dictionary of request headers (case-insensitive keys).
 *
 * Returns:
 *   True if request appears to be from a browser, False otherwise.
 */
export function isBrowserRequest(
    headers: Record<string, unknown>
): boolean {
    const lower = Object.fromEntries(
        Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v])
    );

    const accept = (lower["accept"] ?? "") as string;
    const userAgent = (lower["user-agent"] ?? "") as string;

    return accept.includes("text/html") && userAgent.includes("Mozilla");
}


/**
 * Decodes a payment header.
 *
 * Args:
 *   paymentHeader: The contents of the payment header.
 *
 * Returns:
 *   The parsed payment payload.
 */
export function decodePaymentHeader(paymentHeader: string): PaymentPayload {
    const bytes = toByteArray(paymentHeader);           // base64 decode → Uint8Array
    const jsonStr = new TextDecoder().decode(bytes);    // Uint8Array → string
    return PaymentPayloadSchema.parse(JSON.parse(jsonStr));
}


/**
 * Validates whether the asset in the payment asset header is valid or not.
 *
 * Args:
 *   network: The involved chosen network.
 *   paymentPayload: The provided payment payload.
 *   paymentAssetHeader: The contents of the payment asset header.
 mergedSetup: The current merged setup.
 *
 * Returns:
 *   A tuple (code, address, true) or ("", "", false).
 */
export function validatePaymentAsset(
    network: string,
    paymentPayload: PaymentPayload,
    paymentAssetHeader: string,
    mergedSetup: Y402Setup
): [string, string, boolean] {
    const tokenCodes = mergedSetup.listTokens(network);
    const chainId = mergedSetup.getChainId(network);
    const normalizedHeader = paymentAssetHeader.toLowerCase();

    for (const code of tokenCodes) {
        const [name, , address, version] =
            mergedSetup.getTokenMetadata(network, code);

        const ok = checkSignature(
            name,
            version,
            chainId,
            address,
            paymentPayload.payload.authorization,
            paymentPayload.payload.signature
        );

        if (
            ok &&
            (!normalizedHeader || normalizedHeader === address.toLowerCase())
        ) {
            return [code, address, true];
        }
    }

    return ["", "", false];
}
