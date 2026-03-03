import express from "express";

const app = express();
app.use(express.json({ limit: "1mb" }));

for (const id of ["payments1", "payments2", "payments3"]) {
    app.post(`/api/webhook/${id}`, (req, res) => {
        console.log(`[express-webhook] ${id}:`, JSON.stringify(req.body));
        res.json({ ok: true, endpoint: id });
    });
}

const port = Number(process.env.WEBHOOKS_PORT || "9872");
app.listen(port, () => {
    console.log(`[express-webhook] listening on http://localhost:${port}`);
});
