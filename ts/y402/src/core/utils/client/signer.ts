import { TypedDataDomain, Wallet } from "ethers";

// Minimal EIP-1193 type (only what we need)
export interface Eip1193Provider {
    request(args: { method: string; params?: unknown[] }): Promise<unknown>;
}

// Generic EIP-712 typed data shape
export interface Eip712TypedData {
    domain: TypedDataDomain;
    types: Record<string, Array<{ name: string; type: string }>>;
    primaryType: string;
    message: Record<string, unknown>;
}

// The signer callback type. It holds the callback
// function (which signs a typed message) and the
// available addresses that can be used.
export type TypedDataSigner = {
    sign: (typedData: Eip712TypedData) => Promise<string>;
    addresses: () => Promise<string[]>;
}

function normalizePrivateKey(pk: string): string {
    const trimmed = pk.trim();
    if (trimmed.startsWith("0x")) return trimmed;
    return `0x${trimmed}`;
}

/**
 * Given either:
 *   - a private key string, or
 *   - an EIP-1193 provider,
 * returns a `(typedData) => Promise<signature>` callback.
 */
export function createTypedDataSigner(
    source: string | Eip1193Provider
): TypedDataSigner {
    // --- Case 1: raw private key (local signing via viem) ---
    if (typeof source === "string") {
        const privateKey = normalizePrivateKey(source);
        const wallet = new Wallet(privateKey as string);

        const sign = async (typedData: Eip712TypedData): Promise<string> => {
            const { domain, types, primaryType, message } = typedData;

            // ethers v6 EIP-712 signing
            const signature = await wallet.signTypedData(
                domain,
                { [primaryType]: types[primaryType], ...types }, // see note below
                message
            );

            // returns a 0x-prefixed hex string
            return signature;
        };

        return {
            sign,
            addresses: async (): Promise<string[]> => {
                return [wallet.address];
            }
        }
    }

    // --- Case 2: EIP-1193 provider (remote signing) ---
    const provider = source;

    const sign = async (typedData: Eip712TypedData): Promise<string> => {
        const { message } = typedData;

        // For TransferWithAuthorization, the signer is the "from" address
        const from = (message?.from as string | undefined)?.toLowerCase();
        if (!from) {
            throw new Error(
                'Typed data message must contain a "from" field to infer signer address'
            );
        }

        const json = JSON.stringify(typedData);

        // Prefer v4 -> v3 -> legacy
        // Params order [from, data] is what MetaMask & most wallets expect.
        try {
            const sig = await provider.request({
                method: "eth_signTypedData_v4",
                params: [from, json],
            });
            return sig as string;
        } catch {
            // fall through
        }

        try {
            const sig = await provider.request({
                method: "eth_signTypedData_v3",
                params: [from, json],
            });
            return sig as string;
        } catch {
            // fall through
        }

        // Last resort: legacy eth_signTypedData
        const sig = await provider.request({
            method: "eth_signTypedData",
            params: [from, json],
        });

        return sig as string;
    };

    // Return the full object.
    return {
        sign,
        addresses: async (): Promise<string[]> => {
            return await provider.request({
                method: "eth_getAccounts",
                params: []
            }) as string[];
        }
    }
}
