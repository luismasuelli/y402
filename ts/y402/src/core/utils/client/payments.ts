import { PaymentRequirements } from "../../types/requirements";
import { PaymentError } from "./errors";

/**
 * A default selector of payment requirements.
 * @param requirements
 */
export function defaultPaymentRequirementsSelector(requirements: PaymentRequirements[]): PaymentRequirements {
    for(let requirement of requirements) {
        if (requirement.scheme === "exact") {
            return requirement;
        }
    }
    throw new PaymentError("No supported payment scheme found");
}

/**
 * A payment required selector, which can be an async function,
 * is used to choose a payment from a list of payments.
 */
export type PaymentRequiredSelector =
    ((requirements: PaymentRequirements[]) => PaymentRequirements) |
    ((requirements: PaymentRequirements[]) => Promise<PaymentRequirements>);