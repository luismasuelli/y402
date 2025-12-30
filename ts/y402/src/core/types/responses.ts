import { z } from "zod";
import { PaymentRequirementsSchema } from "./requirements";


/**
 * Response indicating that x402 payment is required.
 */
export const X402PaymentRequiredResponseSchema = z.object({
    x402Version: z.number().int(),
    accepts: z.array(PaymentRequirementsSchema),
    error: z.string(),
});


/**
 * Response indicating that x402 payment is required.
 */
export type X402PaymentRequiredResponse = z.infer<
    typeof X402PaymentRequiredResponseSchema
>;
