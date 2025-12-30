/**
 * This is an adapter over HTTP request clients (e.g. fetch and axios),
 * so the different elements of this stack can rely on this class and
 * their children.
 */
export abstract class HTTPClient {
    /**
     * Sends a request.
     * @param url The URL.
     * @param method The method ("get" by default).
     * @param params The params to send. Optional.
     * @param json The json to send. Optional.
     * @param timeout The timeout.
     * @param throwOnHTTPError Whether to throw error on non-2xx/3xx.
     */
    abstract sendRequest({url, method = "get", params, json, timeout = 0, throwOnHTTPError = true}: {
        url: string, method: string, params?: Record<string, any>, json?: any,
        timeout: number, throwOnHTTPError: boolean
    });
}