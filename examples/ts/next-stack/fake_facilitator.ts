import express from "express";
import crypto from "node:crypto";

const X402_VERSION = 1;
const SUPPORTED = [{ scheme: "exact", network: "local" }];

const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
    res.json({ status: "healthy", service: "dumb-x402-facilitator-next" });
});

app.get("/supported", (_req, res) => {
    res.json({ kinds: SUPPORTED });
});

app.post("/verify", (req, res) => {
    try {
        const body = req.body || {};
        if (body.x402Version !== X402_VERSION) {
            return res.json({ isValid: false, invalidReason: "unsupported_x402_version" });
        }
        if (typeof body.paymentPayload !== "object" || typeof body.paymentRequirements !== "object") {
            return res.json({ isValid: false, invalidReason: "invalid_body" });
        }

        const scheme = body.paymentPayload.scheme;
        const network = body.paymentPayload.network;
        if (scheme !== "exact" || network !== "local") {
            return res.json({ isValid: false, invalidReason: "unsupported_scheme_or_network" });
        }

        const payer = body.paymentPayload?.payload?.authorization?.from;
        return res.json({ isValid: true, invalidReason: null, payer });
    } catch (error) {
        return res.status(400).json({ isValid: false, invalidReason: String(error) });
    }
});

app.post("/settle", (req, res) => {
    try {
        const body = req.body || {};
        if (body.x402Version !== X402_VERSION) {
            return res.json({ success: false, errorReason: "unsupported_x402_version" });
        }

        const payer = body.paymentPayload?.payload?.authorization?.from;
        const network = body.paymentPayload?.network || "local";
        const transaction = `0x${crypto.randomBytes(32).toString("hex")}`;
        return res.json({
            success: true,
            errorReason: null,
            transaction,
            network,
            payer
        });
    } catch (error) {
        return res.status(400).json({ success: false, errorReason: String(error) });
    }
});

const port = Number(process.env.FACILITATOR_PORT || "9874");
app.listen(port, () => {
    console.log(`[next-facilitator] listening on http://localhost:${port}`);
});
