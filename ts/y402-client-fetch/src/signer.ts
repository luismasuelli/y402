import type { Hex, TypedDataDomain } from "viem";
import { privateKeyToAccount } from "viem/accounts";

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

// The signer callback type you asked for
export type TypedDataSigner = (typedData: Eip712TypedData) => Promise<string>;

function normalizePrivateKey(pk: string): Hex {
    const trimmed = pk.trim();
    if (trimmed.startsWith("0x")) return trimmed as Hex;
    return (`0x${trimmed}`) as Hex;
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
        const account = privateKeyToAccount(privateKey);

        return async (typedData: Eip712TypedData): Promise<string> => {
            const { domain, types, primaryType, message } = typedData;

            const signature = await account.signTypedData({
                domain,
                types,
                primaryType: primaryType as any, // keep TS happy with generic types
                message: message as any,
            });

            // viem returns `Hex` (`0x...`) which is already a string
            return signature;
        };
    }

    // --- Case 2: EIP-1193 provider (remote signing) ---
    const provider = source;

    return async (typedData: Eip712TypedData): Promise<string> => {
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
}
