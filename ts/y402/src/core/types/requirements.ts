import { z } from "zod";
import { EIP712DomainSchema } from "./eip712";


/**
 * Represents token asset information including EIP-712
 * domain data.
 */
export const TokenAssetSchema = z.object({
    address: z.string(),
    decimals: z
        .number()
        .int()
        .refine((v) => v >= 0 && v <= 255, {
            message: "decimals must be between 0 and 255",
        }),
    eip712: EIP712DomainSchema,
});


/**
 * Represents token asset information including EIP-712
 * domain data.
 */
export type TokenAsset = z.infer<typeof TokenAssetSchema>;


/**
 * Represents an amount of tokens in atomic units with asset
 * information.
 */
export const TokenAmountSchema = z.object({
    amount: z
        .string()
        .refine(
            (v) => {
                try {
                    BigInt(v);
                    return true;
                } catch {
                    return false;
                }
            },
            {
                message: "amount must be an integer encoded as a string",
            }
        ),
    asset: TokenAssetSchema,
});


/**
 * Represents an amount of tokens in atomic units with asset
 * information.
 */
export type TokenAmount = z.infer<typeof TokenAmountSchema>;


/**
 * Price can be a string, number, or TokenAmount
 */
export const PriceSchema = z.union([z.string(), z.number(), TokenAmountSchema]);


/**
 * Price can be a string, number, or TokenAmount
 */
export type Price = z.infer<typeof PriceSchema>;


/**
 * This is a payment requirement specification that applies
 * for an endpoint in particular.
 */
export const RequirePaymentDetailsSchema = z
    .object({
        scheme: z.literal("exact").default("exact"),
        network: z.string().describe(
            "The human name of the network (e.g. ethereum, ethereum-sepolia, base, base-sepolia, avalanche, avalanche-fuji)"
        ),
        price: PriceSchema.describe(
            "The price, which can be any x402-supported price type"
        ),
        payToAddress: z
            .string()
            .describe("The address to pay to. It must be a valid address")
            .refine((v) => /^0x[a-fA-F0-9]{40}$/.test(v), {
                message: "pay_to_address must be a 0x-prefixed 40-hex digits string",
            }),
    })
    .refine(
        (data) => {
            const v = data.price;

            // TokenAmount
            if (TokenAmountSchema.safeParse(v).success) {
                try {
                    return BigInt((v as any).amount) >= 0n;
                } catch {
                    return false;
                }
            }

            // number
            if (typeof v === "number") return v >= 0;

            // string
            if (typeof v === "string") {
                const s = v.trim();
                const numeric = s[0]?.match(/[0-9.]/) ? s : s.slice(1);
                const num = Number(numeric);
                return !Number.isNaN(num) && num >= 0;
            }

            return false;
        },
        {
            message:
                "The price must be a valid positive numeric str (can be $-prefixed), a positive int, or a positive TokenAmount object",
            path: ["price"],
        }
    );


/**
 * This is a payment requirement specification that applies
 * for an endpoint in particular.
 */
export type RequirePaymentDetails = z.infer<
    typeof RequirePaymentDetailsSchema
>;


/**
 * This is the details of a payment requirement that both
 * server and client agree on.
 */
export const PaymentRequirementsSchema = z
    .object({
        scheme: z
            .string()
            .default("exact")
            .describe("The payment payload scheme, e.g. 'exact'"),
        network: z
            .string()
            .describe("The payment network by name (e.g. 'base', 'base-sepolia')"),
        maxAmountRequired: z
            .string()
            .describe(
                "The decimal representation of the required amount, in terms of the minimal units"
            )
            .refine(
                (v) => {
                    try {
                        BigInt(v);
                        return true;
                    } catch {
                        return false;
                    }
                },
                {
                    message:
                        "max_amount_required must be an integer encoded as a string",
                }
            ),
        resource: z
            .string()
            .describe(
                "The associated canonical resource URL or request URL for this payment"
            ),
        description: z
            .string()
            .describe(
                "The description of this service / the purpose of the payment"
            ),
        mimeType: z
            .string()
            .default("application/json")
            .describe("The associated MIME type for this request"),
        outputSchema: z
            .unknown()
            .optional()
            .describe(
                "The expected schema for this endpoint. Serves as documentation"
            ),
        payTo: z
            .string()
            .describe("The address the payment must be authorized to"),
        maxTimeoutSeconds: z
            .number()
            .int()
            .describe("The maximum time the client is allowed to take before paying"),
        asset: z
            .string()
            .describe(
                "The 0x-prefixed ethereum address of the asset chosen to make the payment in"
            ),
        extra: z
            .record(z.any(), z.unknown())
            .optional()
            .describe(
                "Extra data (typically used to state the EIP-712 domain"
            ),
    });


/**
 * This is the details of a payment requirement that both
 * server and client agree on.
 */
export type PaymentRequirements = z.infer<typeof PaymentRequirementsSchema>;


/**
 * This is a final payment requirement specification
 * that applies for an endpoint in particular.
 */
export const FinalRequiredPaymentDetailsSchema = z.object({
    scheme: z.literal("exact").default("exact").describe("The scheme"),
    network: z
        .string()
        .describe(
            "The human name of the network (e.g. ethereum, ethereum-sepolia, base, base-sepolia, avalanche, avalanche-fuji)"
        ),
    assetAddress: z
        .string()
        .describe("The address of the token asset"),
    amountRequired: z
        .string()
        .describe("The required amount, as an uint256 value"),
    payToAddress: z
        .string()
        .describe("The address to pay to. It must be a valid address"),
    eip712Domain: z
        .record(z.any(), z.unknown())
        .describe(
            "The data related to the eip712 domain for this protocol"
        ),
});


/**
 * This is a final payment requirement specification
 * that applies for an endpoint in particular.
 */
export type FinalRequiredPaymentDetails = z.infer<
    typeof FinalRequiredPaymentDetailsSchema
>;
