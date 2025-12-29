import { z } from "zod";


export const PaymentIdentitySchema = z.object({
    resource: z
        .string()
        .describe(
            `The URL of the resource. This URL is both user-defined and user-configured. \
It has exactly one argument named reference_ticket which can refer an object that can be \
paid once or more (depending on the asset)`
        ),

    tags: z
        .array(z.string())
        .describe(
            `This is a mandatory list of tags which can be used to identify categories \
for the payments. Tags are set once per configuration and are static in nature, since \
they are categories of payment processing. By configuration, one resource URL will relate \
to a set of tags and a given (internal) reference`
        ),

    reference: z
        .string()
        .describe(
            `This is the internal reference code, primarily added into the resource URL, \
as it is used to identify the payment`
        )
});

export type PaymentIdentity = z.infer<typeof PaymentIdentitySchema>;


export const PaymentDetailsSchema = z.object({
    // Canonic fields.
    payer: z
        .string()
        .describe(
            `The 0x-prefixed ethereum address of the account authorizing the payment`
        ),

    chain_id: z
        .string()
        .describe(`The id of the chain, in decimal representation`),

    token: z
        .string()
        .describe(
            `The 0x-prefixed ethereum address of the token contract. It will support \
ERC-3009 or be somehow supported by this payment system`
        ),

    value: z
        .string()
        .describe(
            `The decimal representation of the token amount. It will be expressed in \
the minimal token units according to the decimals supported by the token`
        ),

    pay_to_address: z
        .string()
        .describe(`The address that received the payment`),

    // Representational fields.
    code: z
        .string()
        .describe(`The codename of the token (e.g. usdt, usdc, eurc, eurt)`),

    name: z
        .string()
        .describe(`The display name of the token (e.g. USDt, USDC, EURt, EURC)`),

    price_label: z
        .string()
        .describe(
            `A symbol-based representation of the amount being paid. For example, USDC and USDt \
will represent 150000 as $0.15, while EURC and and EURt will represent 150000 as €0.15. \
Tokens without symbol will use no symbol, representing a fractional number according to their \
decimals, e.g. a 10-decimals token will represent 150000 as 0.000015, without any kind of symbol \
unless one is stated`
        )
});

export type PaymentDetails = z.infer<typeof PaymentDetailsSchema>;


export const SettledPaymentSchema = z.object({
    id: z
        .string()
        .describe(`The unique ID of the payment`),

    version: z
        .number()
        .describe(`The y402 version`),

    identity: PaymentIdentitySchema.describe(
        `The identity of the payment (with identifier and category)`
    ),

    details: PaymentDetailsSchema.describe(
        `The details of the payment (token, network, ...)`
    ),

    // Using ISO 8601 timestamp strings; use z.coerce.date() if Date objects are preferred.
    settled_on: z
        .string()
        .datetime()
        .optional()
        .describe(`The time this payment was settled on`),

    transaction_hash: z
        .string()
        .optional()
        .describe(`The 0x-prefixed transaction hash`)
});

export type SettledPayment = z.infer<typeof SettledPaymentSchema>;
