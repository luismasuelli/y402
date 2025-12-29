import { SettledPayment } from "../types/payment";


/**
 * This class defines a storage manager for the (post-verified) user payment requests.
 */
export abstract class StorageManager<P = unknown, R = unknown> {
    /**
     * Stores an authorization in 'verified' state. It tells the authorization
     * (signed by the `from` sender) and the matched requirement. Ideally, the
     * implementation of this method will store the data in some sort of store
     * where the matched_requirements are a separate table, and the payment id
     * serves as primary key, while the payload contains the whole data.
     *
     * These records serve well to track the evolution of a paid requirement
     * and also address user claims. This also means: this method must NOT fail
     * silently but be violent enough with the payment failing to be stored.
     *
     * The storage manager is totally free to choose other fields for the data
     * (e.g. some sort of tagging) system.
     * @param collection The collection to store the payment into.
     * @param paymentId The id of the payment (generated on the fly).
     * @param payload The client payload fromm headers.
     * @param matchedRequirements The matched requirements.
     * @param settledPayment The settled payment record. It will be sent via
     * webhook after settlement.
     * @param webhookName The associated webhook name to use on launch after
     * settlement.
     */
    abstract allocate(
        collection: string,
        paymentId: string,
        payload: P,
        matchedRequirements: R,
        settledPayment: SettledPayment,
        webhookName: string
    ): void | Promise<void>;

    /**
     * Aborts a payment id, marking its record.
     * @param collection The collection to remove the payment from.
     * @param paymentId The id of the payment to mark.
     */
    abstract abort(collection: string, paymentId: string): void | Promise<void>;

    /**
     * Confirms a given payment id, meaning that the /settle endpoint worked.
     * @param collection The collection to settle the payment into.
     * @param paymentId The id of the payment matching a stored one.
     * @param transaction The hash of the transaction.
     */
    abstract settle(
        collection: string,
        paymentId: string,
        transaction: string
    ): void | Promise<void>;

    /**
     * Returns the current batch of records for the given worker and webhook name.
     * @param collection The collection to batch a payment for a worker.
     * @param webhookName The name of the webhook the records must have to be
     * batched by this method. Many workers may batch for the same webook name.
     * @param workerId The id of the worker to use for batching.
     */
    abstract getBatch(
        collection: string,
        webhookName: string,
        workerId: string
    ): SettledPayment[] | Promise<SettledPayment[]>;

    /**
     * Marks a payment as webhook-sent.
     * @param collection The collection to mark a payment into.
     * @param paymentId The payment id.
     */
    abstract markAsSent(
        collection: string,
        paymentId: string
    ): void | Promise<void>;
}
