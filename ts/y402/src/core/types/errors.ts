/**
 * Base error, for all the error subclasses of this library.
 */
export class BaseError extends Error {
    /**
     * The passed arguments.
     */
    args: any[];

    constructor(...args: any[]) {
        super(args.length === 1 ? (
            (args[0] === null || args[0] === undefined) ? "" : args[0]
        ).toString() : JSON.stringify(args));
        this.args = args;
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
