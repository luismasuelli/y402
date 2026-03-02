import type { AxiosError, AxiosInstance } from "axios";
import { wrapAxiosInstance } from "../src";
import type { TypedDataSigner } from "y402";

if (!(globalThis as any).crypto) {
    (globalThis as any).crypto = {
        getRandomValues(array: Uint8Array) {
            for (let i = 0; i < array.length; i += 1) {
                array[i] = (i + 7) % 255;
            }
            return array;
        }
    };
}

const signer: TypedDataSigner = {
    async sign() {
        return "0xdeadbeef";
    },
    async addresses() {
        return ["0x1111111111111111111111111111111111111111"];
    }
};

let onRejected: ((error: AxiosError) => Promise<any>) | null = null;
let retriedHeaders: Record<string, string> = {};

const fakeAxios = {
    interceptors: {
        response: {
            use: (_onFulfilled: any, reject: any) => {
                onRejected = reject;
                return 0;
            }
        }
    },
    request: async (config: any) => {
        retriedHeaders = config.headers;
        return { status: 200, data: { ok: true } };
    }
} as unknown as AxiosInstance;

async function main() {
    wrapAxiosInstance(fakeAxios, signer, null, null, { "base-sepolia": "84532" });

    if (!onRejected) {
        throw new Error("Expected interceptor reject handler to be installed");
    }

    const error = {
        config: { headers: {} },
        response: {
            status: 402,
            data: {
                x402Version: 1,
                accepts: [
                    {
                        scheme: "exact",
                        network: "base-sepolia",
                        asset: "0x2222222222222222222222222222222222222222",
                        maxAmountRequired: "1000",
                        resource: "http://localhost/resource",
                        description: "Resource",
                        mimeType: "application/json",
                        outputSchema: {},
                        payTo: "0x3333333333333333333333333333333333333333",
                        maxTimeoutSeconds: 60,
                        extra: { name: "USDC", version: "1" }
                    }
                ]
            },
            headers: {
                "x-payment-networks": Buffer.from(JSON.stringify({ "base-sepolia": 84532 }), "utf-8").toString("base64")
            }
        }
    } as unknown as AxiosError;

    const response = await onRejected(error);
    if (response.status !== 200) {
        throw new Error(`Expected 200 but got ${response.status}`);
    }
    if (!retriedHeaders["X-PAYMENT"]) {
        throw new Error("Expected X-PAYMENT on retry request");
    }
    if (retriedHeaders["X-PAYMENT-ASSET"] !== "0x2222222222222222222222222222222222222222") {
        throw new Error("Expected X-PAYMENT-ASSET on retry request");
    }

    console.log("axios manual test passed");
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
