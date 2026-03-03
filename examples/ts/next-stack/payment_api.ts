import { createServer, IncomingHttpHeaders } from "node:http";
import { Y402Setup, type RequirePaymentDetails } from "y402";
import { StorageManager as MongoStorageManager } from "y402-storage-mongodb";
import {
    paymentRequired,
    withX402EndpointSettings,
    type NextRouteHandler,
    type PaymentDetailsType
} from "y402-server-next";

const MONGODB_URL = process.env.MONGODB_URL || "mongodb://root:example@localhost:27517/mydb?authSource=admin";
const PAY_TO_ADDRESS = process.env.SERVER_PAY_TO_ADDRESS || "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC";
const TOKEN_ADDRESS = process.env.SERVER_TOKEN_ADDRESS || "0x0000000000000000000000000000000000000001";
const FACILITATOR_URL = process.env.FACILITATOR_URL || "http://localhost:9874";

const setup = new Y402Setup();
setup.addNetwork("local", 31337);
setup.addToken(
    "local",
    "usdf",
    "USD Fake",
    TOKEN_ADDRESS,
    "1",
    6,
    "$",
    true
);
setup.setDefaultToken("local", "usdf");

const storage = new MongoStorageManager(MONGODB_URL, "payments");

const options = {
    mimeType: "application/json",
    defaultMaxDeadlineSeconds: 60,
    facilitatorConfig: { url: FACILITATOR_URL },
    setup,
    storageManager: storage
};

const paymentDetailsPerType: PaymentDetailsType = (req: Request): RequirePaymentDetails[] => {
    const parts = new URL(req.url).pathname.split("/");
    const type = String(parts[3] || "").toLowerCase();
    const price = type === "bronze" ? "$1" : type === "silver" ? "$3" : type === "gold" ? "$5" : "$1";
    return [{
        scheme: "exact",
        network: "local",
        price,
        payToAddress: PAY_TO_ADDRESS
    }];
};

type Route = {
    pattern: RegExp;
    keys: string[];
    handler: ReturnType<typeof paymentRequired>;
};

function wrap(base: NextRouteHandler): ReturnType<typeof paymentRequired> {
    return paymentRequired(base, options);
}

const routes: Route[] = [
    {
        pattern: /^\/api\/purchase\/([^/]+)$/,
        keys: ["type"],
        handler: wrap(withX402EndpointSettings({
            paymentDetails: paymentDetailsPerType,
            description: "Accepts payments of certain type: gold, silver, bronze",
            mimeType: "application/json",
            tags: ["dynamic", "anonymous"],
            webhookName: "dynamic_type_next",
            storageCollection: "dynamic_type"
        })(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } })))
    },
    {
        pattern: /^\/api\/purchase2\/([^/]+)\/([^/]+)$/,
        keys: ["type", "reference"],
        handler: wrap(withX402EndpointSettings({
            paymentDetails: paymentDetailsPerType,
            referenceParam: "reference",
            description: "Accepts payments of certain type: gold, silver, bronze (tracks reference)",
            mimeType: "application/json",
            tags: ["dynamic", "reference"],
            webhookName: "dynamic_type_next",
            storageCollection: "dynamic_type"
        })(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } })))
    },
    {
        pattern: /^\/api\/purchase3\/fixed$/,
        keys: [],
        handler: wrap(withX402EndpointSettings({
            paymentDetails: [{
                scheme: "exact",
                network: "local",
                price: "$2.5",
                payToAddress: PAY_TO_ADDRESS
            }],
            description: "Accepts payments of fixed type",
            mimeType: "application/json",
            tags: ["fixed", "anonymous"],
            webhookName: "fixed_type_next",
            storageCollection: "fixed_type"
        })(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } })))
    },
    {
        pattern: /^\/api\/purchase4\/fixed\/([^/]+)$/,
        keys: ["reference"],
        handler: wrap(withX402EndpointSettings({
            paymentDetails: [{
                scheme: "exact",
                network: "local",
                price: "$2.5",
                payToAddress: PAY_TO_ADDRESS
            }],
            referenceParam: "reference",
            description: "Accepts payments of fixed type (tracks reference)",
            mimeType: "application/json",
            tags: ["fixed", "reference"],
            webhookName: "fixed_type_next",
            storageCollection: "fixed_type"
        })(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } })))
    }
];

function normalizeHeaders(headers: IncomingHttpHeaders): Record<string, string> {
    const out: Record<string, string> = {};
    for (const [key, value] of Object.entries(headers)) {
        if (typeof value === "string") {
            out[key] = value;
        } else if (Array.isArray(value)) {
            out[key] = value.join(",");
        }
    }
    return out;
}

async function toBuffer(stream: NodeJS.ReadableStream): Promise<Buffer> {
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
        chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    return Buffer.concat(chunks);
}

const port = Number(process.env.API_PORT || "9873");

const server = createServer(async (req, res) => {
    const method = (req.method || "GET").toUpperCase();
    if (method !== "POST") {
        res.statusCode = 404;
        res.end("Not found");
        return;
    }

    const origin = `http://${req.headers.host || `localhost:${port}`}`;
    const pathname = (req.url || "/").split("?")[0];
    const route = routes.find((r) => r.pattern.test(pathname));

    if (!route) {
        res.statusCode = 404;
        res.end("Not found");
        return;
    }

    const match = pathname.match(route.pattern);
    const params: Record<string, string> = {};
    if (match) {
        route.keys.forEach((key, idx) => {
            params[key] = decodeURIComponent(match[idx + 1] || "");
        });
    }

    const body = await toBuffer(req);
    const request = new Request(`${origin}${req.url || "/"}`, {
        method,
        headers: normalizeHeaders(req.headers),
        body: body.length ? body : undefined
    });

    const response = await route.handler(request, { params });
    res.statusCode = response.status;
    response.headers.forEach((value, key) => {
        res.setHeader(key, value);
    });

    const responseBuffer = Buffer.from(await response.arrayBuffer());
    res.end(responseBuffer);
});

server.listen(port, () => {
    console.log(`[next-api-like] listening on http://localhost:${port}`);
    console.log(`[next-api-like] facilitator: ${FACILITATOR_URL}`);
});
