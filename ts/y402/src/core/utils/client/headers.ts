import { ethers } from "ethers";
import { Eip712TypedData, TypedDataSigner } from "./signer";
import { PaymentRequirements } from "../../types/requirements";

function tokenHex(bytes: number = 32): string {
    const r = globalThis.crypto.getRandomValues(new Uint8Array(32));
    return Array.from(r).map((e: number) => e.toString(16).padStart(2, '0')).join("");
}

function safeBase64Encode(data: string): string {
    if (typeof globalThis !== "undefined" && typeof globalThis.btoa === "function") {
        return globalThis.btoa(data);
    }
    return Buffer.from(data).toString("base64");
}

/**
 * Decodes the x-payment-networks header.
 * @param header The header.
 */
export function decodeNetworksHeader(header: string): Record<string, string> {
    const decoded = Buffer.from(header, "base64").toString("utf-8");
    return JSON.parse(decoded) as Record<string, string>;
}

/**
 * Creates a signed header for x402.
 * @param x402Version The version (only `1` is allowed by this point).
 * @param signer The signer, which can have many addresses if it's an EIP-1193-backed object.
 * @param signerAddress The chosen address for the signer. It must be among the signer's addresses.
 * @param requirements The chosen requirements.
 * @param chainIdByName The available mapping name => id of available chains.
 * @returns The signed header, dumped to JSON and encoded as base64.
 */
export async function createSignedHeader(
    x402Version: number,
    signer: TypedDataSigner,
    signerAddress: string,
    requirements: PaymentRequirements,
    chainIdByName: Record<string, string>
): Promise<string> {
    // Check it's a valid network, first.
    if (!(chainIdByName[requirements.network])) {
        throw new Error(`The network '${requirements.network}' is not known among the ` +
                        "client's configured networks and either the server is a regular " +
                        "x402 v1 server, or it does not contain said network among the " +
                        "advertised networks");
    }

    // Prepare the header with the authorization and so.
    let header = {
        x402Version,
        scheme: requirements.scheme,
        network: requirements.network,
        payload: {
            signature: "",
            authorization: {
                from: ethers.getAddress(signerAddress),
                to: ethers.getAddress(requirements.payTo),
                value: requirements.maxAmountRequired,
                validAfter: String(Math.floor(Date.now() / 1000 - 60)),
                validBefore: String(Math.floor(Date.now() / 1000) + requirements.maxTimeoutSeconds),
                nonce: "0x" + tokenHex(),
            },
        },
    }

    // Sign the authorization.
    const dataToSign: Eip712TypedData = {
        "types": {
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ]
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": requirements.extra!["name"] as string,
            "version": requirements.extra!["version"] as string,
            "chainId": Number(chainIdByName[requirements.network]),
            "verifyingContract": requirements.asset,
        },
        "message": {
            ...header.payload.authorization
        }
    };
    let signature = await signer.sign(dataToSign);
    if (!signature.startsWith("0x")) {
        signature = "0x" + signature;
    }

    // Assign the signature to the whole payload.
    header.payload.signature = signature;

    // Finally, encode this header.
    return safeBase64Encode(JSON.stringify(header));
}
