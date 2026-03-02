export * from "./lifecycle";
export * from "./workers";
export * from "./storage/base";
export * from "./storage/dummy";
export * from "./types/payment";

// These things stand for v1 of the protocol.
export * from "./core/types/default_data";
export * from "./core/types/setup";
export * from "./core/types/endpoint_settings";
export * from "./core/types/facilitator";
export * from "./core/types/paywall";
export * from "./core/types/registry";
export * from "./core/types/requirements";
export * from "./core/types/responses";

// Tools used by server libraries.
import * as serverHeaders from "./core/utils/server/headers";
import * as serverPrices from "./core/utils/server/prices";
export const server = {
    headers: serverHeaders,
    prices: serverPrices
};

// Tools used by client libraries.
import * as clientHeaders from "./core/utils/client/headers";
import * as clientSigner from "./core/utils/client/signer";
import * as clientErrors from "./core/utils/client/errors";
import * as clientPayments from "./core/utils/client/payments";
export const client = {
    headers: {
        ...clientHeaders
    },
    signer: {
        ...clientSigner
    },
    errors: {
        ...clientErrors
    },
    payments: {
        ...clientPayments
    }
};
export type TypedDataSigner = clientSigner.TypedDataSigner;
export type Eip1193Provider = clientSigner.Eip1193Provider;
export type Eip712TypedData = clientSigner.Eip712TypedData;
export type PaymentRequiredSelector = clientPayments.PaymentRequiredSelector;
export type { PaymentPayload } from "./core/types/client";