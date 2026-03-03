# TypeScript-side examples

This folder mirrors the Python examples style with two stacks:

- `express-stack/`
- `next-stack/`

Each stack contains:
- `dumb_webhooks.ts`
- `fake_facilitator.ts`
- `payment_api.ts`

There are also shared-style companions:
- `front-end/front_end.ts` to trigger paid calls
- `workers/worker.ts` to forward settled payments to webhook endpoints

## 1) Start MongoDB

From `examples/ts`:

```bash
docker compose -f docker-compose.mongodb.yml up
```

## 2) Install package dependencies

Install for each folder you plan to run:

```bash
cd express-stack && npm install
cd ../next-stack && npm install
cd ../front-end && npm install
cd ../workers && npm install
```

Each example folder also ships its own `tsconfig.json` with Node typings.
If your IDE still caches old TS settings, restart TS server after install.

## 3) Launch one stack (Express or Next-like)

### Express stack

In separate terminals:

```bash
cd examples/ts/express-stack
npm run webhooks
```

```bash
cd examples/ts/express-stack
npm run facilitator
```

```bash
cd examples/ts/express-stack
npm run api
```

### Next-like stack

In separate terminals:

```bash
cd examples/ts/next-stack
npm run webhooks
```

```bash
cd examples/ts/next-stack
npm run facilitator
```

```bash
cd examples/ts/next-stack
npm run api
```

## 4) Trigger paid calls (frontend script)

```bash
cd examples/ts/front-end
FRONTEND_INTERNAL_CLIENT_LIBRARY=fetch FRONTEND_SERVER_TYPE=express npm run start
```

or

```bash
cd examples/ts/front-end
FRONTEND_INTERNAL_CLIENT_LIBRARY=axios FRONTEND_SERVER_TYPE=next npm run start
```

## 5) Launch workers

For Express stack examples:

```bash
cd examples/ts/workers
WORKER_WEBHOOK_NAME=dynamic_type_express WORKER_WEBHOOK_URL=/api/webhook/payments1 npm run start
```

For Next-like stack examples:

```bash
cd examples/ts/workers
WORKER_WEBHOOK_NAME=fixed_type_next WORKER_WEBHOOK_URL=/api/webhook/payments2 npm run start
```

## Environment variables

### Common server vars

- `SERVER_TOKEN_ADDRESS` (required): payment token contract address.
- `SERVER_PAY_TO_ADDRESS` (optional): defaults to Anvil account #2 `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC`.

### Facilitator vars

- `FACILITATOR_PORT` (optional): default `9874` for next-like stack, `9876` for express stack.

### Front-end vars

- `FRONTEND_INTERNAL_CLIENT_LIBRARY`: `fetch` or `axios`.
- `FRONTEND_SERVER_TYPE`: `express` or `next`.
- `FRONTEND_PRIVATE_KEY` (optional): defaults to Anvil account #1 private key.

### Worker vars

- `WORKER_WEBHOOK_NAME`: one of `dynamic_type_express`, `fixed_type_express`, `dynamic_type_next`, `fixed_type_next`.
- `WORKER_WEBHOOK_URL`: `/api/webhook/payments1`, `/api/webhook/payments2`, or `/api/webhook/payments3`.
- `WORKER_ID` (optional): default `my-awesome-worker`.
