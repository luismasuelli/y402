import axios, {AxiosInstance, AxiosRequestConfig} from "axios";
import { StorageManager } from "y402/src/storage/base";
import type { SettledPayment } from "y402/src/types/payment";

// Minimal logger interface; you can adapt to your logging setup.
export interface Logger {
    info: (...args: any[]) => void;
    error: (...args: any[]) => void;
}

async function maybeAwait<T>(value: T | Promise<T>): Promise<T> {
    return value;
}

const defaultLogger: Logger = console;


async function sendBatch(
    workerId: string,
    webhookName: string,
    webhookUrl: string,
    apiKey: string,
    manager: StorageManager,
    collection: string,
    logger: Logger
): Promise<void> {
    const trimmedApiKey = apiKey.trim();
    const headers: Record<string, string> = trimmedApiKey
        ? { "X-API-Key": trimmedApiKey } as Record<string, string>
        : {};

    logger.info("Processing a batch:");
    logger.info("- Retrieving the batch...");

    const batch: SettledPayment[] = await maybeAwait(manager.getBatch(collection, webhookName, workerId));

    logger.info(`- Sending the batch (${batch.length} elements)...`);

    const client: AxiosInstance = axios.create({
        timeout: 15_000
    });

    const sendOne = async (payload: SettledPayment): Promise<void> => {
        try {
            const response = await client.post(
                webhookUrl, payload,{ headers } as AxiosRequestConfig
            );
            // Throws if HTTP status >= 400
            // (axios throws automatically on non-2xx by default)
            await maybeAwait(manager.markAsSent(collection, payload.id));
        } catch (err) {
            logger.error(
                `An exception occurred when processing payment with id=${payload.id}`,
                err
            );
        }
    };

    await Promise.all(batch.map(sendOne));

    // NOTE: The original Python code calls mark_as_sent again in a loop
    // after the batch send. That is effectively redundant if mark_as_sent
    // is idempotent (only transitions to "finished" once), so this version
    // just marks when each send succeeds. If you want strict parity, we
    // could add an extra loop here.
}

/**
 * Runs the webhook worker loop (async).
 *
 * This is the equivalent of Python's `_webhook_worker`.
 * It loops forever until an error occurs or the caller cancels/ends the process.
 */
export async function webhookWorker(
    workerId: string,
    webhookName: string,
    webhookUrl: string,
    apiKey: string,
    storageManager: StorageManager,
    collection: string,
    logger: Logger = defaultLogger,
    sleepTimeSeconds: number = 5
): Promise<void> {
    logger.info(
        `Starting webhook worker loop.\n- webhook_name=${webhookName}\n- worker_id=${workerId}`
    );

    const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    try {
        // Infinite loop; caller is responsible for process-level cancellation.
        // (e.g. SIGINT or an AbortSignal wrapper).
        // This mirrors the Python "while True" behavior.
        // eslint-disable-next-line no-constant-condition
        while (true) {
            await sendBatch(
                workerId,
                webhookName,
                webhookUrl,
                apiKey,
                storageManager,
                collection,
                logger
            );
            await sleep(sleepTimeSeconds * 1000);
        }
    } catch (err) {
        logger.error("Worker loop stopped because of an error:", err);
    }
}
