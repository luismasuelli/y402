import { z } from "zod";
import { PAYWALL_TEMPLATE } from "./template";
import { X402_VERSION } from "../../types/constants";
import { PaymentRequirementsSchema, type PaymentRequirements } from "../../types/requirements";
import { type PaywallConfig } from "../../types/paywall";


// Shape of the window.x402 configuration
export const X402ConfigSchema = z.object({
    amount: z.number(),
    paymentRequirements: PaymentRequirementsSchema.array(),
    testnet: z.boolean(),
    currentUrl: z.string(),
    error: z.string(),
    x402_version: z.string(),
    cdpClientKey: z.string(),
    appName: z.string(),
    appLogo: z.string(),
    sessionTokenEndpoint: z.string(),
});


export type X402Config = z.infer<typeof X402ConfigSchema>;


// Allow TypeScript to know about window.x402
declare global {
    interface Window {
        x402?: X402Config;
    }
}


/**
 * Create x402 configuration object from payment requirements.
 * @param error The error to show.
 * @param paymentRequirements The list of supported requirements.
 * @param paywallConfig Optional configuration for the CDP paywall.
 * @returns The final config to use.
 */
export function createX402Config(
    error: string,
    paymentRequirements: PaymentRequirements[],
    paywallConfig?: PaywallConfig | null,
): X402Config {
    const requirements = paymentRequirements[0] ?? null;

    let displayAmount = 0;
    let currentUrl = "";
    let testnet = true;

    if (requirements) {
        // Convert atomic amount back to USD (assuming USDC with 6 decimals)
        const rawAmount = Number(
            // max_amount_required in Python; adapt to your field name if different
            (requirements as any).max_amount_required ?? requirements.maxAmountRequired,
        );

        if (Number.isFinite(rawAmount)) {
            displayAmount = rawAmount / 1_000_000; // USDC has 6 decimals
        } else {
            displayAmount = 0;
        }

        currentUrl = requirements.resource ?? "";
        testnet = requirements.network === "base-sepolia";
    }

    // Get paywall config values or defaults
    const config = paywallConfig ?? ({} as PaywallConfig);

    const baseConfig: X402Config = X402ConfigSchema.parse({
        amount: displayAmount,
        paymentRequirements,
        testnet,
        currentUrl,
        error,
        x402_version: X402_VERSION,
        cdpClientKey: (config as any).cdp_client_key ?? "",
        appName: (config as any).app_name ?? "",
        appLogo: (config as any).app_logo ?? "",
        sessionTokenEndpoint: (config as any).session_token_endpoint ?? "",
    });

    // Validate/normalize with Zod at runtime (optional but keeps things strict)
    return X402ConfigSchema.parse(baseConfig);
}

/**
 * Injects payment requirements into HTML as JavaScript variables.
 * @param htmlContent The HTML content to insert.
 * @param error Error message to display.
 * @param paymentRequirements List of payment requirements.
 * @param paywallConfig Optional paywall UI configuration.
 * @returns The final contents.
 */
export function injectPaymentData(
    htmlContent: string,
    error: string,
    paymentRequirements: PaymentRequirements[],
    paywallConfig?: PaywallConfig | null,
): string {
    // Create x402 configuration object
    const x402Config = createX402Config(error, paymentRequirements, paywallConfig);

    // Create the configuration script (matching the Python/TS pattern)
    const logOnTestnet = x402Config.testnet
        ? "console.log('Payment requirements initialized:', window.x402);"
        : "";

    const configScript = `
  <script>
    window.x402 = ${JSON.stringify(x402Config)};
    ${logOnTestnet}
  </script>`;

    // Inject the configuration script into the head
    return htmlContent.replace("</head>", `${configScript}\n</head>`);
}


/**
 * Load paywall HTML and inject payment data.
 * @param error Error message to display.
 * @param paymentRequirements List of payment requirements.
 * @param paywallConfig Optional paywall UI configuration.
 * @returns Complete HTML with injected payment data.
 */
export function getPaywallHtml(
    error: string,
    paymentRequirements: PaymentRequirements[],
    paywallConfig?: PaywallConfig | null,
): string {
    return injectPaymentData(PAYWALL_TEMPLATE, error, paymentRequirements, paywallConfig);
}
