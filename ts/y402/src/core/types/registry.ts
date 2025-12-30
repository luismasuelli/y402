import { Y402_ENDPOINT_SETTINGS, X402EndpointSettings } from "./endpoint_settings";
import { Y402Setup } from "./setup";


/**
 * This is a registry of endpoints, under a single middleware,
 * and the support for their networks and tokens.
 *
 * It works like a lazy retriever of endpoint-related custom data.
 * For each endpoint that is queried, its extended support data
 * is generated and retrieved.
 */
export class FinalEndpointSetupRegistry {
    private _fullDataByEndpoint: WeakMap<Function, Y402Setup>;
    private _middlewareCustomSetup?: Y402Setup | null;

    constructor(middlewareCustomSetup?: Y402Setup | null) {
        this._fullDataByEndpoint = new WeakMap();
        this._middlewareCustomSetup = middlewareCustomSetup ?? null;
    }

    /**
     * Retrieves the effective Y402Setup for a given endpoint.
     *
     * If the endpoint has never been seen before, its settings are
     * inspected (via the Y402_ENDPOINT_SETTINGS property), and the
     * final setup is computed by merging:
     *
     *   - The middleware-level custom setup (if any), and
     *   - The endpoint-level custom setup (if any).
     *
     * The result is cached per endpoint.
     */
    get(endpoint: Function): Y402Setup {
        const cached = this._fullDataByEndpoint.get(endpoint);
        if (cached) {
            return cached;
        }

        const endpointSettings = (endpoint as any)[
            Y402_ENDPOINT_SETTINGS
            ] as X402EndpointSettings | undefined;

        const endpointCustomSetup: Y402Setup | null =
            endpointSettings?.customSetup ?? null;

        let setup: Y402Setup;
        if (this._middlewareCustomSetup && endpointCustomSetup) {
            setup = this._middlewareCustomSetup.or(endpointCustomSetup);
        } else {
            setup =
                this._middlewareCustomSetup ||
                endpointCustomSetup ||
                new Y402Setup();
        }

        this._fullDataByEndpoint.set(endpoint, setup);
        return setup;
    }

    /**
     * Python-style indexer sugar: registry[endpoint]
     * You can use this if you like the []-style ergonomics.
     */
    public readonly at = (endpoint: Function) => this.get(endpoint);
}
