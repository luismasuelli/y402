import axios from "axios";
import { client } from "y402";
import { wrapFetch } from "y402-client-fetch";
import { wrapAxiosInstance } from "y402-client-axios";

const PRIVATE_KEY = process.env.FRONTEND_PRIVATE_KEY
    || "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d";
const INTERNAL_CLIENT_LIBRARY = (process.env.FRONTEND_INTERNAL_CLIENT_LIBRARY || "fetch").toLowerCase();
const SERVER_TYPE = (process.env.FRONTEND_SERVER_TYPE || "express").toLowerCase();

const baseUrl = SERVER_TYPE === "next"
    ? "http://localhost:9873"
    : "http://localhost:9875";

if (!["fetch", "axios"].includes(INTERNAL_CLIENT_LIBRARY)) {
    throw new Error("Invalid FRONTEND_INTERNAL_CLIENT_LIBRARY: must be fetch or axios");
}
if (!["express", "next"].includes(SERVER_TYPE)) {
    throw new Error("Invalid FRONTEND_SERVER_TYPE: must be express or next");
}

function randomHex(size: number): string {
    const alpha = "0123456789abcdef";
    let result = "";
    for (let i = 0; i < size; i += 1) {
        result += alpha[Math.floor(Math.random() * alpha.length)]!;
    }
    return result;
}

async function main() {
    const type = ["gold", "silver", "bronze"][Math.floor(Math.random() * 3)]!;
    const reference = randomHex(10);

    const chosen = [
        "/api/purchase/<type>",
        "/api/purchase2/<type>/<reference>",
        "/api/purchase3/fixed",
        "/api/purchase4/fixed/<reference>"
    ][Math.floor(Math.random() * 4)]!;

    const path = chosen
        .replace("<type>", type)
        .replace("<reference>", reference);

    const url = `${baseUrl}${path}`;
    console.log(`Triggering URL: ${url}`);

    const signer = client.signer.createTypedDataSigner(PRIVATE_KEY);

    if (INTERNAL_CLIENT_LIBRARY === "fetch") {
        const paymentFetch = wrapFetch(globalThis.fetch, signer, null, null, null);
        const response = await paymentFetch(url, { method: "POST" });
        console.log("POST result:");
        console.log(">>> Status:", response.status);
        console.log(">>> Headers:", Object.fromEntries(response.headers.entries()));
        const text = await response.text();
        try {
            console.log(">>> JSON:", JSON.parse(text));
        } catch {
            console.log(">>> Content:", text);
        }
        return;
    }

    const clientAxios = wrapAxiosInstance(axios.create(), signer, null, null, null);
    const response = await clientAxios.post(url);
    console.log("POST result:");
    console.log(">>> Status:", response.status);
    console.log(">>> Headers:", response.headers);
    console.log(">>> JSON:", response.data);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
