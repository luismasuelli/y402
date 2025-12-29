import { MongoClient, Db, Collection } from "mongodb";
import { StorageManager as BaseStorageManager } from "y402/src/storage/base";
import { SettledPaymentSchema } from "y402/src/types/payment";
import type { SettledPayment } from "y402/src/types/payment";


const DEFAULT_BATCH_SIZE = 50;
const DEFAULT_BATCH_EXPIRATION_SECONDS = 60;


/**
 * A MongoDB-based storage manager.
 */
export class StorageManager<P = unknown, R = unknown> extends BaseStorageManager<P, R> {
    private client: MongoClient;
    private db: Db;
    private batchExpirationSeconds: number;
    private batchExpirationMs: number;
    private batchSize: number;

    /**
     * A MongoDB-based storage manager.
     *
     * @param url MongoDB connection string.
     * @param database Database name.
     * @param batchExpiration Batch “freshness window” in seconds.
     * @param batchSize Maximum number of records per batch.
     */
    constructor(
        url: string,
        database: string,
        batchExpiration: number = DEFAULT_BATCH_EXPIRATION_SECONDS,
        batchSize: number = DEFAULT_BATCH_SIZE
    ) {
        super();

        const trimmedUrl = url.trim();
        const trimmedDb = database.trim();

        if (!trimmedUrl || !trimmedDb) {
            throw new Error(
                "Both URL and database must be specified for a MongoDB-based StorageManager"
            );
        }

        this.client = new MongoClient(trimmedUrl);
        this.db = this.client.db(trimmedDb);

        this.batchExpirationSeconds =
            Number.isInteger(batchExpiration)
                ? Math.max(DEFAULT_BATCH_EXPIRATION_SECONDS, batchExpiration)
                : DEFAULT_BATCH_EXPIRATION_SECONDS;

        this.batchExpirationMs = this.batchExpirationSeconds * 1000;

        this.batchSize =
            Number.isInteger(batchSize)
                ? Math.max(DEFAULT_BATCH_SIZE, batchSize)
                : DEFAULT_BATCH_SIZE;
    }

    /**
     * Gets an underlying collection.
     * @param name The collection name.
     * @returns The underlying collection.
     * @private
     */
    private collection(name: string): Collection {
        return this.db.collection(name);
    }

    /**
     * Stores an authorization in 'verified' state.
     * @param collection The collection to store the payment into.
     * @param paymentId The id of the payment (generated on the fly).
     * @param payload The client payload fromm headers.
     * @param matchedRequirements The matched requirements.
     * @param settledPayment The settled payment record. It will be sent
     * via webhook after settlement.
     * @param webhookName The associated webhook name to use on launch
     * after settlement.
     * @returns Nothing (async function).
     */
    async allocate(
        collection: string,
        paymentId: string,
        payload: P,
        matchedRequirements: R,
        settledPayment: SettledPayment,
        webhookName: string
    ): Promise<void> {
        const collection_ = this.collection(collection);

        // Indexes (errors ignored, as in Python)
        try {
            await collection_.createIndex({ payment_id: "hashed" }, { unique: true });
        } catch {
            /* ignore */
        }

        try {
            await collection_.createIndex({ webhook_name: "hashed" });
        } catch {
            /* ignore */
        }

        try {
            await collection_.createIndex({ status: "hashed" });
        } catch {
            /* ignore */
        }

        // Ensure payload is valid SettledPayment; type-level it should already be,
        // but this keeps it aligned with your Zod schema.
        const webhookPayload = SettledPaymentSchema.parse(settledPayment);

        await collection_.insertOne({
            payment_id: String(paymentId),
            payload,                 // already a plain JS object in TS land
            matched_requirements: matchedRequirements,
            status: "verified",
            webhook_payload: webhookPayload,
            webhook_name: webhookName,
            created_on: new Date()   // JS Date is UTC-based
        });
    }

    /**
     * Aborts a payment id, marking its record.
     * @param collection The collection to remove the payment from.
     * @param paymentId The id of the payment to remove.
     * @returns Nothing (async function).
     */
    async abort(collection: string, paymentId: string): Promise<void> {
        const collection_ = this.collection(collection);

        // NOTE: This uses $set, which is the logically-correct version of your
        // Python `update_one(..., {"status": "aborted"})` (which would overwrite
        // the document).
        await collection_.updateOne(
            { payment_id: String(paymentId) },
            { $set: { status: "aborted" } }
        );
    }

    /**
     * Confirms a given payment id, meaning that the /settle endpoint worked.
     * @param collection The collection to commit / confirm the payment into.
     * @param paymentId The id of the payment matching a stored one.
     * @param transaction The hash of the transaction.
     * @returns Nothing (async function).
     */
    async settle(
        collection: string,
        paymentId: string,
        transaction: string
    ): Promise<void> {
        await this.collection(collection).updateOne(
            { payment_id: String(paymentId) },
            {
                $set: {
                    status: "settled",
                    "webhook_payload.transaction_hash": transaction,
                    "webhook_payload.settled_on": new Date()
                }
            }
        );
    }

    /**
     * Internal helper to batch a single element.
     */
    private async _batchOne(
        collection: string,
        webhookName: string,
        workerId: string,
        stamp: Date
    ): Promise<boolean> {
        const minDate = new Date(stamp.getTime() - this.batchExpirationMs);

        const result = await this.collection(collection).findOneAndUpdate(
            {
                status: "settled",
                webhook_name: webhookName,
                $or: [
                    { batched_on: { $exists: false } },
                    { batched_on: { $lte: minDate } },
                    { worker: { $exists: false } },
                    { worker: { $in: ["", null] } }
                ]
            },
            { $set: { worker: workerId, batched_on: stamp } }
        );

        return result?.value != null;
    }

    /**
     * Returns the current batch of records for the given worker and webhook name.
     * @param collection The collection to batch a payment for a worker.
     * @param webhookName The name of the webhook the records must have to be
     * batched by this method. Many workers may batch for the same webook name.
     * @param workerId The id of the worker to use for batching.
     * @returns A list of the requests to send to that webhook.
     * @returns The list of settled payments to be sent.
     */
    async getBatch(
        collection: string,
        webhookName: string,
        workerId: string
    ): Promise<SettledPayment[]> {
        const batchSize = this.batchSize;
        const stamp = new Date();
        const minDate = new Date(stamp.getTime() - this.batchExpirationMs);

        const coll = this.collection(collection);

        // 2. Count already-batched items.
        const alreadyBatchedCount = await coll.countDocuments({
            status: "settled",
            webhook_name: webhookName,
            worker: workerId,
            batched_on: { $gt: minDate }
        });

        // 2b. Batch remaining items.
        if (alreadyBatchedCount < batchSize) {
            const toBatch = batchSize - alreadyBatchedCount;
            for (let i = 0; i < toBatch; i++) {
                const ok = await this._batchOne(collection, webhookName, workerId, stamp);
                if (!ok) {
                    break;
                }
            }
        }

        // 3. Return the records.
        const cursor = coll.find({
            status: "settled",
            webhook_name: webhookName,
            worker: workerId,
            batched_on: { $gt: minDate }
        });

        const result: SettledPayment[] = [];
        for await (const doc of cursor) {
            // doc._id is irrelevant to the webhook payload.
            const payload = doc.webhook_payload;
            if (!payload) continue;

            // Validate/normalize through Zod before returning.
            result.push(SettledPaymentSchema.parse(payload));
        }

        return result;
    }

    /**
     * Marks a payment as webhook-sent.
     * @param collection The collection to mark a payment into.
     * @param paymentId The payment id.
     * @returns Nothing (async function).
     */
    async markAsSent(
        collection: string,
        paymentId: string
    ): Promise<void> {
        await this.collection(collection).updateOne(
            {
                status: "settled",
                payment_id: String(paymentId)
            },
            { $set: { status: "finished" } }
        );
    }
}
