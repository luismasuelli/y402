import { PaymentRequirements, type TypedDataSigner, createTypedDataSigner, createSignedHeader } from "y402";

// Exports this signer, so it can be used by the customers.
export { createTypedDataSigner };

/**
 * The payment error.
 */
export class PaymentError extends Error {
    constructor(message: string) {
        super(message);
    }
}

/**
 * Decodes a JSON header.
 * @param header The header.
 */
function decodeHeader(header: string): string {
    const decoded = Buffer.from(header, "base64").toString("utf-8");
    return JSON.parse(decoded);
}

/**
 * A default selector of payment requirements
 * @param requirements
 */
function defaultPaymentRequirementsSelector(requirements: PaymentRequirements[]): PaymentRequirements {
    for(let requirement of requirements) {
        if (requirement.scheme === "exact") {
            return requirement;
        }
    }
    throw new PaymentError("No supported payment scheme found");
}

/**
 * A payment required selector, which can be an async function,
 * is used to choose a payment from a list of payments.
 */
export type PaymentRequiredSelector =
    ((requirements: PaymentRequirements[]) => PaymentRequirements) |
    ((requirements: PaymentRequirements[]) => Promise<PaymentRequirements>);

/**
 * Creates a wrapped version of fetch, which uses x402 when
 * the endpoint's flow requires it. This requires the following
 * elements:
 * 1. The original fetch function, or another wrapper.
 * 2. The signer, created with createTypedDataSigner.
 * 3. A function that chooses an address, which must be among (await signer.addresses()).
 * 4. A selector over the payments.
 * 5. Optionally, a default mapping of chain ids by their names.
 */
export function wrapFetch(
    fetch: typeof globalThis.fetch,
    signer: TypedDataSigner,
    signerAddressSelector: (() => Promise<string>) | null,
    paymentRequiredSelector: PaymentRequiredSelector | null = null,
    chainIdByName: Record<string, string> | null = null
) {
    paymentRequiredSelector ||= defaultPaymentRequirementsSelector;
    signerAddressSelector ||= async () => {
        const addresses = await signer.addresses();
        if (!addresses.length) {
            throw new PaymentError("The signer does not have any available address");
        }
        return addresses[0];
    }

    return async (input, init) => {
        // First, execute the naive call. If it does not return
        // a 402 call, return.
        const response = await fetch(input, init);
        if (response.status !== 402) {
            return response;
        }

        // Retrieve the data of that response.
        const { x402Version, accepts } = (await response.json()) as {
            x402Version: number;
            accepts: unknown[];
        };
        if (x402Version !== 1) {
            throw new PaymentError("This client only works on x402 v1");
        }

        // Get the X-Payment-Networks response header.
        const xPaymentNetworksHeader = response.headers.get("X-Payment-Networks")
        let chainIdByName_ = null;
        try {
            chainIdByName_ = xPaymentNetworksHeader ? decodeHeader(xPaymentNetworksHeader) : null;
        } catch {}
        chainIdByName_ ||= chainIdByName || {};

        // Get the selected payment, or complain.
        const selected: PaymentRequirements = await paymentRequiredSelector!(accepts || []);

        // Make the payment header.
        const address: string = await signerAddressSelector!();
        const paymentHeader = await createSignedHeader(
            x402Version, signer, address, selected, chainIdByName_
        );

        // Send the new request.
        const newInit = {
            ...init,
            headers: {
                ...init.headers || {},
                "X-PAYMENT": paymentHeader,
                "X-PAYMENT-ASSET": selected.asset,
                "Access-Control-Expose-Headers": "X-PAYMENT-RESPONSE, X-PAYMENT-NETWORKS"
            }
        };
        return await fetch(input, newInit);
    }
}