import { z } from "zod";

/**
 * Configuration for paywall UI customization.
 */
export const PaywallConfigSchema = z.object({
    cdp_client_key: z.string().optional(),
    app_name: z.string().optional(),
    app_logo: z.string().optional(),
    session_token_endpoint: z.string().optional(),
});

export type PaywallConfig = z.infer<typeof PaywallConfigSchema>;
