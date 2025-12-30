import { MisconfigurationError } from "./errors";
import { KNOWN_NETWORKS_AND_TOKENS } from "./default_data";


type TokenMeta = {
    name: string;
    symbol: string;
    address: string;
    version: string;
    decimals: number;
};


type NetworkEntry = {
    chain_id: number;
    tokens: Record<string, TokenMeta>;
    tokens_by_address: Record<string, string>;
    default_token: string | null;
};


/**
 * A setup tells in a set of internal mappings:
 *
 * - The available networks.
 * - The tokens in those networks.
 */
export class Y402Setup {
    private _networks: Record<string, NetworkEntry>;
    private _default_tokens: Record<string, Record<string, string>>;

    constructor() {
        this._networks = {};
        this._default_tokens = {};
    }

    /**
     * Adds a network spec to the current setup. This
     * is done by telling which network and also the
     * chain id, but the chain id can be omitted if
     * the network is known (in fact: it will be not
     * considered, but replaced / reset, if it's for
     * a known network name).
     *
     * Args:
     *   network: The network id.
     *   chain_id: The chain id.
     */
    addNetwork(network: string, chainId: number = 0): void {
        network = network.trim().toLowerCase();

        if (network in this._networks) {
            throw new MisconfigurationError(
                `This network is already set up: ${network}`
            );
        }

        const known = KNOWN_NETWORKS_AND_TOKENS[network];
        if (known && chainId < 1) {
            chainId = known.chain_id;
        }

        if (chainId < 1) {
            throw new MisconfigurationError(
                `Invalid chain id for network key: ${network}`
            );
        }

        this._networks[network] = {
            chain_id: chainId,
            tokens: {},
            tokens_by_address: {},
            default_token: null,
        };
    }

    /**
     * Adds a token contract to a specific place.
     *
     * Args:
     *   network: The network name for which the token will be added.
     *   code: An internal name for this contract, like "usdc". Given
     *         an existing network and a known code, adding it will
     *         just use the names of the known data, optionally with
     *         some overrides (e.g. the version).
     *   name: A name for this contract. It may be chosen, e.g. "USDC".
     *   address: The address of the token.
     *   version: The EIP-712 version of the token. If the token is
     *            an EIP-3009 token it should have a version. Try
     *            "1" by default if not, or a value that is sensible
     *            for the contract itself when trying.
     *   decimals: The amount of decimals of the token. It MUST match
     *             the value returned at .decimals() in the token.
     *   symbol: A symbol for this contract, like $ or €. It is optional.
     *   default_for_symbol: Whether the current token will be resolved
     *                       to be the one to use when its symbol is
     *                       used in a price with that symbol (or no
     *                       symbol, perhaps).
     */
    addToken(
        network: string,
        code: string,
        // The name.
        name: string = "",
        // The address and the version.
        address: string = "",
        version: string = "",
        // The decimals and the symbol.
        decimals: number = 0,
        symbol: string = "",
        // Whether it's default or not.
        default_for_symbol: boolean = false
    ): void {
        network = network.trim().toLowerCase();
        code = code.trim().toLowerCase();

        if (!(network in this._networks)) {
            throw new MisconfigurationError(
                `This network is not yet set up: ${network}`
            );
        }
        if (!code) {
            throw new MisconfigurationError(`Use a valid code for the token`);
        }
        if (code in this._networks[network].tokens) {
            throw new MisconfigurationError(
                `This token is already set up in network ${network}: ${code}`
            );
        }
        if (" 0123456789.".includes(symbol) || symbol.length > 1) {
            throw new MisconfigurationError(`Invalidd symbol: ${symbol}`);
        }

        const knownNetwork = KNOWN_NETWORKS_AND_TOKENS[network];
        if (knownNetwork && knownNetwork.tokens && code in knownNetwork.tokens) {
            const knownToken = knownNetwork.tokens[code];
            decimals = decimals || knownToken.decimals;
            version = version || knownToken.eip712Version;
            symbol = symbol || knownToken.symbol;
            address = address || knownToken.address;
            name = name || knownToken.name;
        }

        name = name.trim() || code.toUpperCase();
        if (!address || !version || decimals < 0 || !name) {
            throw new MisconfigurationError(
                `One or more token arguments are missing`
            );
        }
        if (address in this._networks[network].tokens_by_address) {
            throw new MisconfigurationError(
                `This token's address is already setup in network ${network}: ${address}`
            );
        }

        const tokenData: TokenMeta = {
            name,
            symbol,
            address,
            version,
            decimals,
        };

        this._networks[network].tokens[code] = tokenData;
        this._networks[network].tokens_by_address[address] = code;

        if (default_for_symbol) {
            if (!this._default_tokens[network]) {
                this._default_tokens[network] = {};
            }
            this._default_tokens[network][symbol] = code;
        }
    }

    /**
     * Checks the chosen network and token code to exist.
     *
     * Args:
     *   network: The network name for which the token will be added.
     *   code: An internal name for an existing token contract in the
     *         network in this setup.
     */
    private _check_network_and_code(
        network: string,
        code: string
    ): [string, string] {
        network = network.trim().toLowerCase();
        code = code.trim().toLowerCase();

        if (!(network in this._networks)) {
            throw new MisconfigurationError(
                `This network is not yet set up: ${network}`
            );
        }
        if (!code) {
            throw new MisconfigurationError(`Use a valid code for the token`);
        }
        if (!(code in this._networks[network].tokens)) {
            throw new MisconfigurationError(
                `This token is not yet set up in network ${network}: ${code}`
            );
        }

        return [network, code];
    }

    /**
     * Given a network code and a token code, it ensures the token
     * becomes the default one for its symbol (even if for some
     * reason no symbol were to be defined in a token).
     *
     * Args:
     *   network: The network name for which the token will be added.
     *   code: An internal name for an existing token contract in the
     *         network in this setup.
     */
    setDefaultForSymbolToken(network: string, code: string): void {
        const [net, c] = this._check_network_and_code(network, code);
        const token = this._networks[net].tokens[c];
        const symbol = token.symbol;

        if (!this._default_tokens[net]) {
            this._default_tokens[net] = {};
        }
        this._default_tokens[net][symbol] = c;
    }

    /**
     * Given a network code and a token code, it ensures the token
     * becomes the default one, this time not for its symbol but
     * instead for when an integer value is used.
     *
     * Args:
     *   network: The network name for which the token will be defaulted.
     *   code: An internal name for an existing token contract in the
     *         network in this setup.
     */
    setDefaultToken(network: string, code: string): void {
        const [net, c] = this._check_network_and_code(network, code);
        this._networks[net].default_token = c;
    }

    /**
     * Gets the default token of a network
     *
     * Args:
     *   network: The network name for which the token will be defaulted.
     *
     * Returns:
     *   The default token code of that network.
     */
    getDefaultToken(network: string): string | null {
        if (!(network in this._networks)) {
            return null;
        }
        return this._networks[network].default_token;
    }

    /**
     * Builds a price label for an amount of a given currency.
     *
     * Args:
     *   value: A decimal representation of the amount.
     *   decimals: The amount of digits that are decimal places.
     *   symbol: The currency symbol.
     *
     * Returns:
     *   A textual representation.
     */
    private _get_price_label(value: string, decimals: number, symbol: string) {
        const d = Number(value) / Math.pow(10, decimals);
        return `${symbol}${d}`;
    }

    /**
     * Returns the list of registered token (codes) for a network.
     *
     * Args:
     *   network: The network name for which the tokens will be listed.
     *
     * Returns:
     *   The list of registered tokens.
     */
    listTokens(network: string): string[] {
        network = network.trim().toLowerCase();
        if (!(network in this._networks)) {
            throw new MisconfigurationError(
                `This network is not yet set up: ${network}`
            );
        }
        return Object.keys(this._networks[network].tokens);
    }

    /**
     * Returns the metadata associated to a token.
     *
     * Args:
     *   network: The network name for which the token will be defaulted.
     *   code: An internal name for an existing token contract in the
     *         network in this setup.
     *
     * Returns:
     *   The associated metadata.
     */
    getTokenMetadata(
        network: string,
        code: string
    ): [string, string, string, string, number] {
        const [net, c] = this._check_network_and_code(network, code);
        const token = this._networks[net].tokens[c];
        return [
            token.name,
            token.symbol,
            token.address,
            token.version,
            token.decimals,
        ];
    }

    /**
     * Returns data associated to a specific token payment.
     *
     * Args:
     *   network: The name of the network.
     *   token: The address of the token contract.
     *   value: A decimal representation of the amount.
     *
     * Returns:
     *   A tuple (chain_id, code, name, price_label).
     */
    getPaymentData(
        network: string,
        token: string,
        value: string
    ): [number, string, string, string] {
        network = network.trim().toLowerCase();
        if (!(network in this._networks)) {
            throw new MisconfigurationError(
                `This network is not yet set up: ${network}`
            );
        }
        if (!(token in this._networks[network].tokens_by_address)) {
            throw new MisconfigurationError(`Use a valid code for the token`);
        }

        const code = this._networks[network].tokens_by_address[token];
        const tokenData = this._networks[network].tokens[code];
        const decimals = tokenData.decimals;
        const name = tokenData.name;
        const chainId = this._networks[network].chain_id;
        const symbol = tokenData.symbol;

        return [
            chainId,
            code,
            name,
            this._get_price_label(value, decimals, symbol),
        ];
    }

    /**
     * Given a network, returns its chain id.
     *
     * Args:
     *   network: The name of the network.
     *
     * Returns:
     *   An integer being the chain id.
     */
    getChainId(network: string): number {
        try {
            return this._networks[network].chain_id;
        } catch {
            throw new MisconfigurationError(
                `This network is not set up: ${network}`
            );
        }
    }

    /**
     * Returns the available mapping of name => chain_id.
     *
     * Returns:
     *   A dictionary mapping name => chain_id from this setup.
     */
    getChainIdsMapping(): Record<string, number> {
        const result: Record<string, number> = {};
        for (const [key, value] of Object.entries(this._networks)) {
            result[key] = value.chain_id;
        }
        return result;
    }

    /**
     * Given a price label, it tries to parse it.
     *
     * Args:
     *   network: The name of the network.
     *   label: The label to parse.
     *
     * Returns:
     *   The parsed token price, as (asset code, amount).
     */
    parsePriceLabel(network: string, label: string): [string, string] {
        label = label.trim();
        if (!label) {
            return ["", "0"];
        }

        // 1. Parse the symbol and get the token.
        let symbol: string;
        let price: string;
        if (!"0123456789.".includes(label[0])) {
            symbol = label[0];
            price = label.slice(1);
        } else {
            symbol = "";
            price = label;
        }

        if (
            !this._default_tokens[network] ||
            !(symbol in this._default_tokens[network])
        ) {
            throw new MisconfigurationError(
                `The symbol '${symbol}' is not default-registered in network: ${network}`
            );
        }

        const code = this._default_tokens[network][symbol];
        const tokenData = this._networks[network].tokens[code];
        const decimals = tokenData.decimals;

        // 2. Parse the price and multiply by decimals to get the amount.
        try {
            const d = Number(price);
            if (!Number.isFinite(d) || d < 0) {
                throw new Error("Invalid Price");
            }
            const amount = String(Math.trunc(d * Math.pow(10, decimals)));
            // 3. Return the token code and the amount.
            return [code, amount];
        } catch {
            throw new MisconfigurationError(
                `The price '${price} is not a valid amount`
            );
        }
    }

    /**
     * Merges two definitions (as a new definition) when doing this. The
     * definitions in the first operand take precedence when defining
     * networks and tokens, but the definitions in the second operand
     * take precedence when defining defaults.
     *
     * :param other: The other setup to merge.
     * :return: The new, merged, definition.
     */
    or(other: Y402Setup): Y402Setup {
        const merged = new Y402Setup();

        for (const obj of [this, other]) {
            for (const [network, values] of Object.entries(obj._networks)) {
                const chainId = values.chain_id;
                const tokens = values.tokens;

                // First, add the network.
                try {
                    merged.addNetwork(network, chainId);
                } catch {
                    // ignore if already present
                }

                // Then, add the tokens.
                for (const [code, tokenData] of Object.entries(tokens)) {
                    const { name, symbol, address, version, decimals } = tokenData;
                    try {
                        merged.addToken(
                            network,
                            code,
                            name,
                            address,
                            version,
                            decimals,
                            symbol
                        );
                    } catch {
                        // ignore if already present
                    }
                }

                // Finally, add the defaults. The defaults
                // in the other setup will take precedence.
                const defaults = obj._default_tokens[network];
                if (defaults) {
                    for (const [symbol, code] of Object.entries(defaults)) {
                        merged.setDefaultForSymbolToken(network, code);
                    }
                }
            }
        }

        return merged;
    }
}
