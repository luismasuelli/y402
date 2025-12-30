import type { SettledPayment } from "../types/payment";
import { StorageManager } from "./base";


/**
 * A dummy storage manager.
 *
 * No-op implementation of all StorageManager methods. Used for testing or
 * as a placeholder dependency where a real storage manager is not required.
 */
export class DummyStorageManager<P = unknown, R = unknown> extends StorageManager<P, R> {
    allocate(
        collection: string,
        paymentId: string,
        payload: P,
        matchedRequirements: R,
        settledPayment: SettledPayment,
        webhookName: string
    ): void {
        // no-op
    }

    abort(
        collection: string,
        paymentId: string
    ): void {
        // no-op
    }

    settle(
        collection: string,
        paymentId: string,
        transaction: string
    ): void {
        // no-op
    }

    batchOne(
        collection: string,
        webhookName: string,
        workerId: string,
        batchSize: number
    ): boolean {
        return false;
    }

    getBatch(
        collection: string,
        webhookName: string,
        workerId: string
    ): SettledPayment[] {
        return [];
    }

    markAsSent(
        collection: string,
        paymentId: string
    ): void {
        // no-op
    }
}
