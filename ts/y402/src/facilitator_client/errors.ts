import { BaseError } from "../core/types/errors";


/**
 * Raised when there was an error related to a facilitator.
 */
export class BaseFacilitatorError extends BaseError {}


/**
 * Raised when there was an error creating the facilitator headers.
 */
export class HeadersBuildingFacilitatorError extends BaseFacilitatorError {}


/**
 * Raised when the verification returned a non-2xx error.
 */
export class VerifyBadResponse extends BaseFacilitatorError {}


/**
 * Raised when the verification failed (i.e. it's invalid).
 */
export class VerifyFacilitatorInvalidError extends BaseFacilitatorError {}


/**
 * Raised when the verification had an error.
 */
export class VerifyFacilitatorUnknownError extends BaseFacilitatorError {}


/**
 * Raised when the settling returned a non-2xx error.
 */
export class SettleBadResponse extends BaseFacilitatorError {}


/**
 * Raised when the settling had an error.
 */
export class SettleFacilitatorFailedError extends BaseFacilitatorError {}


/**
 * Raised when the settling had an error.
 */
export class SettleFacilitatorUnknownError extends BaseFacilitatorError {}
