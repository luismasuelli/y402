import { wrapFetch } from "../src";
import type { TypedDataSigner } from "y402";

if (!(globalThis as any).crypto) {
    (globalThis as any).crypto = {
        getRandomValues(array: Uint8Array) {
            for (let i = 0; i < array.length; i += 1) {
                array[i] = (i + 17) % 255;
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

let callCount = 0;
let paymentHeaderSeen = "";
let paymentAssetSeen = "";

const fakeFetch: typeof fetch = async (_input: any, init?: RequestInit) => {
    callCount += 1;

    if (callCount === 1) {
        return new Response(
            JSON.stringify({
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
            }),
            {
                status: 402,
                headers: {
                    "Content-Type": "application/json",
                    "X-Payment-Networks": Buffer.from(JSON.stringify({ "base-sepolia": 84532 }), "utf-8").toString("base64")
                }
            }
        );
    }

    const headers = new Headers(init?.headers || {});
    paymentHeaderSeen = headers.get("X-PAYMENT") || "";
    paymentAssetSeen = headers.get("X-PAYMENT-ASSET") || "";

    return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
    });
};

async function main() {
    const wrapped = wrapFetch(fakeFetch, signer, null, null, { "base-sepolia": "84532" });
    const response = await wrapped("http://localhost/resource", { method: "GET" });

    if (response.status !== 200) {
        throw new Error(`Expected 200 but got ${response.status}`);
    }
    if (!paymentHeaderSeen) {
        throw new Error("Expected X-PAYMENT to be set on retry request");
    }
    if (paymentAssetSeen !== "0x2222222222222222222222222222222222222222") {
        throw new Error("Expected X-PAYMENT-ASSET to be set on retry request");
    }

    console.log("fetch manual test passed");
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
