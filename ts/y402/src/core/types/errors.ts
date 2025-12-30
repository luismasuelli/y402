/**
 * Base error, for all the error subclasses of this library.
 */
export class BaseError extends Error {
    constructor(message?: string) {
        super(message);
        this.name = new.target.name;
    }
}

/**
 * Raised when a configuration error occurs.
 */
export class MisconfigurationError extends BaseError {}

/**
 * Raised when an import error of a conditionally-required
 * library (e.g. FastAPI, requests) occurs.
 */
export class ConditionalDependencyError extends BaseError {}
