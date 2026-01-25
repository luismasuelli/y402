import { MisconfigurationError } from "../types/errors";
import {
    FinalRequiredPaymentDetails,
    RequirePaymentDetails,
    Price,
    TokenAmount, FinalRequiredPaymentDetailsSchema,
} from "../types/requirements";
import { Y402Setup } from "../types/setup";


/**
 * Tells that an error occurred while computing the
 * price of an endpoint.
 */
export class PriceComputingError extends Error {
    constructor(message: string) {
        super(message);
        this.name = "PriceComputingError";
    }
}


type Eip712DomainInfo = {
    name: string;
    version: string;
};


type ResolvedPaymentPrice = [
    amount: FinalRequiredPaymentDetails["amountRequired"],
    assetAddress: string,
    eip712Domain: Eip712DomainInfo,
];


function isTokenAmount(price: Price): price is TokenAmount {
    return (
        typeof price === "object" &&
        price !== null &&
        "amount" in price &&
        "asset" in price
    );
}

/**
 * Internal helper that resolves the price specification into:
 * [amount (atomic units), token address, eip712 domain info]
 */
function resolvePaymentPrice(
    network: string,
    price: Price,
    setup: Y402Setup,
): ResolvedPaymentPrice {
    if (typeof price === "string") {
        try {
            const [code, amount] = setup.parsePriceLabel(network, price);
            const [name, _symbol, address, version] = setup.getTokenMetadata(
                network,
                code,
            );

            return [
                amount as ResolvedPaymentPrice[0],
                address,
                { name, version },
            ];
        } catch (err) {
            console.error(err);
            throw new PriceComputingError(
                "There was an error while computing a price from string",
            );
        }
    }

    if (typeof price === "number") {
        const code = setup.getDefaultToken(network);

        if (code == null) {
            throw new MisconfigurationError(
                `The network ${network} does not have a default token`,
            );
        }

        try {
            const [name, _symbol, address, version] = setup.getTokenMetadata(
                network,
                code,
            );

            return [
                price.toString() as ResolvedPaymentPrice[0],
                address,
                { name, version },
            ];
        } catch (err) {
            console.error(err);
            throw new PriceComputingError(
                "There was an error while computing a price from int",
            );
        }
    }

    if (isTokenAmount(price)) {
        // TokenAmount type - already in atomic units with asset info.
        return [
            price.amount,
            price.asset.address,
            {
                name: price.asset.eip712.name,
                version: price.asset.eip712.version,
            },
        ] as ResolvedPaymentPrice;
    }

    throw new Error(`Invalid price type: ${typeof price}`);
}

/**
 * Resolves a final payment based on a price specification.
 * @param requiredPayment The required payment to base the final payment on.
 * @param setup The final setup for an endpoint.
 * @returns The final payment requirement.
 */
export function resolveFinalPayment(
    requiredPayment: RequirePaymentDetails,
    setup: Y402Setup,
): FinalRequiredPaymentDetails {
    const [amount, address, eip712Domain] = resolvePaymentPrice(
        requiredPayment.network,
        requiredPayment.price,
        setup,
    );

    // Build the final payment requirement object.
    return FinalRequiredPaymentDetailsSchema.parse({
        scheme: requiredPayment.scheme,
        network: requiredPayment.network,
        pay_to_address: requiredPayment.payToAddress,
        asset_address: address,
        amount_required: amount,
        eip712_domain: eip712Domain,
    });
}
