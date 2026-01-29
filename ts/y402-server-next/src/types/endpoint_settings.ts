import { z } from "zod";
import {
    RequirePaymentDetails,
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
 * The settings for a single endpoint. It also works as a decorator
 * to set the settings into a specific endpoint, which should return
 * a quick response based on the reference and nothing else, since
 * by its arrival the payment was already sent to the webhook. This
 * schema extends the previous one by adding the payment details.
 */
export const X402EndpointSettingsSchema = BaseX402EndpointSettingsSchema.extend({
    paymentDetails: z.custom<PaymentDetailsType>()
});
export type X402EndpointSettings = z.infer<typeof X402EndpointSettingsSchema>;

/**
 * The decorator to apply these settings.
 * @param settings The settings to apply.
 */
export function withX402EndpointSettings(settings: X402EndpointSettings) {
    return baseWithX402EndpointSettings<X402EndpointSettings>(settings);
}