import { z } from "zod";

/**
 * EIP-712 domain information for token signing.
 */
export const EIP712DomainSchema = z.object({
    name: z.string(),
    version: z.string(),
});

export type EIP712Domain = z.infer<typeof EIP712DomainSchema>;
