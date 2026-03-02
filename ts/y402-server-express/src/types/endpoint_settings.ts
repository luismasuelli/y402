import type { Request } from "express";
import { z } from "zod";
import {
    RequirePaymentDetails,
    Y402_ENDPOINT_SETTINGS as BASE_Y402_ENDPOINT_SETTINGS,
    X402EndpointSettingsSchema as BaseX402EndpointSettingsSchema,
    withX402EndpointSettings as baseWithX402EndpointSettings
} from "y402";

/**
 * This is a setting which can be a constant value or a callable
 * returning the final value of accepted payment methods.
 */
export type PaymentDetailsType =
    | RequirePaymentDetails[]
    | ((req: Request) => (RequirePaymentDetails[] | Promise<RequirePaymentDetails[]>));

/**
 * The settings for a single endpoint.
 */
export const X402EndpointSettingsSchema = BaseX402EndpointSettingsSchema.extend({
    paymentDetails: z.custom<PaymentDetailsType>()
});

export type X402EndpointSettings = z.infer<typeof X402EndpointSettingsSchema>;
export const Y402_ENDPOINT_SETTINGS = BASE_Y402_ENDPOINT_SETTINGS;

/**
 * The decorator to apply these settings.
 * @param settings The settings to apply.
 */
export function withX402EndpointSettings(settings: X402EndpointSettings) {
    return baseWithX402EndpointSettings(settings);
}
