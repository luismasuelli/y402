import { Y402_VERSION } from "../core/types/constants";

import {
    PaymentIdentitySchema,
    PaymentDetailsSchema,
    SettledPaymentSchema
} from "../types/payment";

import type {
    PaymentIdentity,
    PaymentDetails,
    SettledPayment
} from "../types/payment";

/**
 * This utility lets the user create a settled payment, out
 * of the input data and values.
 * @param paymentId The internal / tracking id of the payment.
 * @param resource The resource URL.
 * @param tags The associated payment tags.
 * @param reference The external / public reference of the payment.
 * @param payer The address of the payer.
 * @param chainId The chain id.
 * @param token The token contract's address.
 * @param value The value.
 * @param payToAddress The address that received the payment.
 * @param code The codename of the token (optional, or "" - typically provided).
 * @param name The name of the token (optional, or "" - typically provided).
 * @param priceLabel The price label of this payment.
 * @returns A settled payment record.
 */
export function createSettledPayment(
    paymentId: string,
    // Identity
    resource: string,
    tags: string[],
    reference: string,
    // Canonical payment details
    payer: string,
    chainId: number,
    token: string,
    value: string,
    payToAddress: string,
    // Descriptive data
    code: string,
    name: string,
    priceLabel: string
): SettledPayment {
    const identity: PaymentIdentity = PaymentIdentitySchema.parse({
        resource,
        tags,
        reference
    });

    const details: PaymentDetails = PaymentDetailsSchema.parse({
        payer,
        chain_id: String(chainId),
        token,
        value,
        pay_to_address: payToAddress,
        code,
        name,
        price_label: priceLabel
    });

    return SettledPaymentSchema.parse({
        id: paymentId,
        version: Y402_VERSION,
        identity,
        details
    });
}
