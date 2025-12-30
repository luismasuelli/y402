import { z } from "zod";


/**
 * This class stands for an EIP-3009 authorization body, without the signature.
 */
export const EIP3009AuthorizationSchema = z.object({
    from: z
        .string()
        .describe("The address sending the token"),
    to: z
        .string()
        .describe("The address that will receive the tokens"),
    value: z
        .string()
        .describe(
            "The amount being send, as a decimal representation of minimal units"
        )
        .refine((v) => {
            try {
                // EVM amounts can be > Number.MAX_SAFE_INTEGER, so use BigInt
                BigInt(v);
                return true;
            } catch {
                return false;
            }
        }, { message: "value must be an integer encoded as a string" }),
    validAfter: z
        .string()
        .describe(
            "An EVM-compatible number, as a decimal representation, being the first instant of validity for the signature"
        ),
    validBefore: z
        .string()
        .describe(
            "An EVM-compatible number, as a decimal representation, being the last instant of validity for the signature"
        ),
    nonce: z
        .string()
        .describe(
            "A decimal representation of the nonce for this authorization"
        )
});


/**
 * This class stands for an EIP-3009 authorization body, without the signature.
 */
export type EIP3009Authorization = z.infer<typeof EIP3009AuthorizationSchema>;


/**
 * This class stands for the client-chosen payload from the server.
 */
export const SchemePayloadSchema = z.object({
    signature: z
        .string()
        .describe("The 0x-prefixed hexadecimal value of the signature"),
    authorization: EIP3009AuthorizationSchema.describe(
        "The authorization payload matching the signature"
    )
});


/**
 * This class stands for the client-chosen payload from the server.
 */
export type SchemePayload = z.infer<typeof SchemePayloadSchema>;


/**
 * This class stands for the full client-provided payment payload.
 */
export const PaymentPayloadSchema = z.object({
    x402Version: z
        .number()
        .int()
        .default(1)
        .describe("The payment payload version, e.g. 1"),
    scheme: z
        .string()
        .default("exact")
        .describe("The payment payload scheme, e.g. 'exact'"),
    network: z
        .string()
        .describe("The payment network by name (e.g. 'base', 'base-sepolia')"),
    payload: SchemePayloadSchema.describe(
        "The payment payload. This one does NOT include the contract's address, so different supported per-network addresses should be tried (unless hinted otherwise) to tell which token this signature belongs to"
    )
});


/**
 * This class stands for the full client-provided payment payload.
 */
export type PaymentPayload = z.infer<typeof PaymentPayloadSchema>;
