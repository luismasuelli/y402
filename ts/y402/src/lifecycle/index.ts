import { v4 as uuidv4 } from "uuid";
import { StorageManager } from "../storage/base";
import { PaymentPayload } from "../core/types/client";
import {
    VerifyRequest,
    FacilitatorConfig,
    SettleRequest,
    SettleResponse,
} from "../core/types/facilitator";
import { PaymentRequirements } from "../core/types/requirements";
import { Y402Setup } from "../core/types/setup";
import { FacilitatorClient } from "../facilitator_client"; // your fetch-based subclass
import { createSettledPayment } from "./utils";
import { X402_VERSION } from "../core/types/constants";


async function maybeAwait<T>(result: T | Promise<T>): Promise<T> {
    return result;
}


/**
 * Processes a given payment.
 * @param resource The (PUBLIC) resource URL.
 * @param tags The tags that apply.
 * @param reference The reference that applies.
 * @param endpoint The (wrapped) endpoint to invoke.
 * @param payment The user-submitted payment.
 * @param matchedRequirements The matched requirements.
 * @param setup An existing Y402 setup.
 * @param facilitatorConfig The facilitator config to use to create a client.
 * @param storageManager The storage manager for payments.
 * @param storageCollection The collection to store the payment into.
 * @param webhookName The name of the webhook.
 * @param requestTimeout The timeout for requests.
 * @returns The processed UUID for this payment. Also, the settle response, if any.
 * Finally, the underlying response from the endpoint. If the response is not a
 * [200..399] response, settle response will be null.
 */
export async function processPayment(
    // The identity of the payment.
    resource: string,
    tags: string[],
    reference: string,
    endpoint: (
        paymentId: string,
    ) => [any, boolean] | Promise<[any, boolean]>,
    // User payment selection.
    payment: PaymentPayload,
    matchedRequirements: PaymentRequirements,
    // External components.
    setup: Y402Setup,
    facilitatorConfig: FacilitatorConfig,
    // Storage.
    storageManager: StorageManager,
    storageCollection: string,
    // Webhook-related data.
    webhookName: string,
    // Tunings.
    requestTimeout = 15,
): Promise<[string, SettleResponse | null, any]> {
    // 1. Prepare all the data for a settled payment. Do this in advance
    //    so no failures are spotted later, on settling, on this topic.
    const payer = payment.payload.authorization.from;
    const network = payment.network;
    const token = matchedRequirements.asset;
    const value = payment.payload.authorization.value;

    const [chainId, code, name, priceLabel] = setup.getPaymentData(
        network,
        token,
        value,
    );

    const paymentId = uuidv4();

    const settledPayment = createSettledPayment(
        paymentId,
        resource,
        tags,
        reference,
        payer,
        chainId,
        token,
        value,
        payment.payload.authorization.to,
        code,
        name,
        priceLabel,
    );

    // 2. Create the facilitator client.
    const facilitatorClient = new FacilitatorClient(facilitatorConfig);

    // 3. Perform the verification.
    const verifyRequest: VerifyRequest = {
        x402Version: X402_VERSION,
        paymentPayload: payment,
        paymentRequirements: matchedRequirements
    };

    await facilitatorClient.verify(verifyRequest, requestTimeout);

    // 4. Store the verified payment.
    await maybeAwait(
        storageManager.allocate(
            storageCollection,
            paymentId,
            payment,
            matchedRequirements,
            settledPayment,
            webhookName,
        ),
    );

    // 5. Execute the underlying endpoint.
    const [response, success] = await maybeAwait(endpoint(paymentId));

    let settleResponse: SettleResponse | null;

    if (success) {
        // 6. Settle the payment.
        const settleRequest: SettleRequest = {
            x402Version: X402_VERSION,
            paymentPayload: payment,
            paymentRequirements: matchedRequirements
        };

        settleResponse = await facilitatorClient.settle(
            settleRequest,
            requestTimeout,
        );

        // 7. If settlement succeeded, mark as settled in storage.
        if (settleResponse.success) {
            await maybeAwait(
                storageManager.settle(
                    storageCollection,
                    paymentId,
                    settleResponse.transaction as string,
                ),
            );
        }
    } else {
        settleResponse = null;
        await maybeAwait(storageManager.abort(storageCollection, paymentId));
    }

    return [paymentId, settleResponse, response];
}
