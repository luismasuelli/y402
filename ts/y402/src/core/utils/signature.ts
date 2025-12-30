import {
    verifyTypedData,
    TypedDataDomain,
    TypedDataField,
} from "ethers";
import { EIP3009Authorization } from "../types/client";


export function checkSignature(
    name: string,
    version: string,
    chainId: number,
    asset: string,
    authorization: EIP3009Authorization,
    signature: string
): boolean {
    // --- Domain (EIP-712) ---
    const domain: TypedDataDomain = {
        name,
        version,
        chainId,
        verifyingContract: asset,
    };

    // --- Types ---
    // Matches Python definition exactly
    const types: Record<string, TypedDataField[]> = {
        TransferWithAuthorization: [
            { name: "from", type: "address" },
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "validAfter", type: "uint256" },
            { name: "validBefore", type: "uint256" },
            { name: "nonce", type: "bytes32" },
        ],
    };

    // --- Message ---
    const message = {
        from: authorization.from,
        to: authorization.to,
        value: authorization.value,
        validAfter: authorization.validAfter,
        validBefore: authorization.validBefore,
        nonce: authorization.nonce,
    };

    // --- Recover signer ---
    let recovered: string;
    try {
        recovered = verifyTypedData(domain, types, message, signature);
    } catch (err) {
        console.error(err);
        return false;
    }

    return recovered.toLowerCase() === authorization.from.toLowerCase();
}
