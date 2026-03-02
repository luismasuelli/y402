import { AxiosInstance, AxiosError } from "axios";
import {
    PaymentRequirements, client,
    type TypedDataSigner,
    type PaymentRequiredSelector
} from "y402";

/**
 * Enables the payment of APIs using the x402 payment protocol by
 * wrapping an axios instance.
 * @param axiosClient - The Axios instance to add the interceptor to.
 * @param signer 2. The signer, created with createTypedDataSigner.
 * @param signerAddressSelector A function that chooses an address, which must be among (await signer.addresses()).
 * @param paymentRequiredSelector A selector over the payments.
 * @param chainIdByName Optionally, a default mapping of chain ids by their names. *
 */
export function wrapAxiosInstance(
    axiosClient: AxiosInstance,
    signer: TypedDataSigner,
    signerAddressSelector: (() => Promise<string>) | null,
    paymentRequiredSelector: PaymentRequiredSelector | null = null,
    chainIdByName: Record<string, string> | null = null
) {
    paymentRequiredSelector ||= client.payments.defaultPaymentRequirementsSelector;
    signerAddressSelector ||= async () => {
        const addresses = await signer.addresses();
        if (!addresses.length) {
            throw new client.errors.PaymentError("The signer does not have any available address");
        }
        return addresses[0];
    };

    axiosClient.interceptors.response.use(
        response => response,
        async (error: AxiosError) => {
            if (!error.response || error.response.status !== 402) {
                return Promise.reject(error);
            }

            try {
                const originalConfig = error.config;
                if (!originalConfig || !originalConfig.headers) {
                    return Promise.reject(new Error("Missing axios request configuration"));
                }

                if ((originalConfig as { __is402Retry?: boolean }).__is402Retry) {
                    return Promise.reject(error);
                }

                const { x402Version, accepts } = error.response.data as {
                    x402Version: number;
                    accepts: PaymentRequirements[];
                };
                if (x402Version !== 1) {
                    return Promise.reject(new client.errors.PaymentError("This client only works on x402 v1"));
                }

                // Get the X-Payment-Networks response header.
                const xPaymentNetworksHeader = error.response.headers["x-payment-networks"];
                let chainIdByName_ = null;
                try {
                    chainIdByName_ = xPaymentNetworksHeader ? client.headers.decodeNetworksHeader(xPaymentNetworksHeader) : null;
                } catch {}
                chainIdByName_ ||= chainIdByName || {};

                // Get the selected payment, or complain.
                const selected: PaymentRequirements = (
                    await paymentRequiredSelector!(accepts as PaymentRequirements[] || [])
                );

                // Make the payment header.
                const address: string = await signerAddressSelector!();
                const paymentHeader = await client.headers.createSignedHeader(
                    x402Version, signer, address, selected, chainIdByName_
                );

                (originalConfig as { __is402Retry?: boolean }).__is402Retry = true;
                originalConfig.headers["X-PAYMENT"] = paymentHeader;
                originalConfig.headers["X-PAYMENT-ASSET"] = selected.asset;
                originalConfig.headers["Access-Control-Expose-Headers"] = "X-PAYMENT-RESPONSE, X-PAYMENT-NETWORKS";

                return await axiosClient.request(originalConfig);
            } catch (paymentError) {
                return Promise.reject(paymentError);
            }
        },
    );

    return axiosClient;
}
