import express, { Request, Response } from "express";
import { Y402Setup, type RequirePaymentDetails } from "y402";
import { StorageManager as MongoStorageManager } from "y402-storage-mongodb";
import {
    paymentRequired,
    withX402EndpointSettings,
    type PaymentDetailsType
} from "y402-server-express";

const MONGODB_URL = process.env.MONGODB_URL || "mongodb://root:example@localhost:27517/mydb?authSource=admin";
const PAY_TO_ADDRESS = process.env.SERVER_PAY_TO_ADDRESS || "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC";
const TOKEN_ADDRESS = process.env.SERVER_TOKEN_ADDRESS || "0x0000000000000000000000000000000000000001";
const FACILITATOR_URL = process.env.FACILITATOR_URL || "http://localhost:9876";

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

const app = express();
app.use(express.json({ limit: "1mb" }));

const paymentDetailsPerType: PaymentDetailsType = (req: Request): RequirePaymentDetails[] => {
    const type = String(req.params.type || "").toLowerCase();
    const price = type === "bronze" ? "$1" : type === "silver" ? "$3" : type === "gold" ? "$5" : "$1";
    return [{
        scheme: "exact",
        network: "local",
        price,
        payToAddress: PAY_TO_ADDRESS
    }];
};

app.post("/api/purchase/:type", paymentRequired(withX402EndpointSettings({
    paymentDetails: paymentDetailsPerType,
    description: "Accepts payments of certain type: gold, silver, bronze",
    mimeType: "application/json",
    tags: ["dynamic", "anonymous"],
    webhookName: "dynamic_type_express",
    storageCollection: "dynamic_type"
})(async (_req: Request, res: Response) => {
    res.json({ ok: true });
}), options));

app.post("/api/purchase2/:type/:reference", paymentRequired(withX402EndpointSettings({
    paymentDetails: paymentDetailsPerType,
    referenceParam: "reference",
    description: "Accepts payments of certain type: gold, silver, bronze (tracks reference)",
    mimeType: "application/json",
    tags: ["dynamic", "reference"],
    webhookName: "dynamic_type_express",
    storageCollection: "dynamic_type"
})(async (_req: Request, res: Response) => {
    res.json({ ok: true });
}), options));

app.post("/api/purchase3/fixed", paymentRequired(withX402EndpointSettings({
    paymentDetails: [{
        scheme: "exact",
        network: "local",
        price: "$2.5",
        payToAddress: PAY_TO_ADDRESS
    }],
    description: "Accepts payments of fixed type",
    mimeType: "application/json",
    tags: ["fixed", "anonymous"],
    webhookName: "fixed_type_express",
    storageCollection: "fixed_type"
})(async (_req: Request, res: Response) => {
    res.json({ ok: true });
}), options));

app.post("/api/purchase4/fixed/:reference", paymentRequired(withX402EndpointSettings({
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
    webhookName: "fixed_type_express",
    storageCollection: "fixed_type"
})(async (_req: Request, res: Response) => {
    res.json({ ok: true });
}), options));

const port = Number(process.env.API_PORT || "9875");
app.listen(port, () => {
    console.log(`[express-api] listening on http://localhost:${port}`);
    console.log(`[express-api] facilitator: ${FACILITATOR_URL}`);
});
