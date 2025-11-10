from y402.core.types.errors import MisconfigurationError


KNOWN_DATA = {
    "abstract": {
        "chain_id": 2741
    },
    "abstract-testnet": {
        "chain_id": 11124
    },
    "base": {
        "chain_id": 8453
    },
    "base-sepolia": {
        "chain_id": 84532
    },
    "avalanche": {
        "chain_id": 43114
    },
    "avalanche-fuji": {
        "chain_id": 43113
    },
    "sei": {
        "chain_id": 1329
    },
    "sei-testnet": {
        "chain_id": 1328
    },
    "polygon": {
        "chain_id": 137
    },
    "polygon-amoy": {
        "chain_id": 80002
    },
    "iotex": {
        "chain_id": 4689
    },
    "peaq": {
        "chain_id": 3338
    }
}


class Y402Setup:
    """
    A setup tells in a set of internal mappings:

    - The available networks.
    - The tokens in those networks.
    """

    def __init__(self):
        self._networks = {}

    def add_network(self, network: str, chain_id: int = 0):
        """
        Adds a network spec to the current setup. This
        is done by telling which network and also the
        chain id, but the chain id can be omitted if
        the network is known (in fact: it will be not
        considered, but replaced / reset, if it's for
        a known network name).

        Args:
            network: The network id.
            chain_id: The chain id.
        """

        network = network.strip().lower()
        if network in self._networks:
            raise MisconfigurationError(f"This network is already set up: {network}")
        if network in KNOWN_DATA and chain_id < 1:
            chain_id = KNOWN_DATA[network]["chain_id"]
        if chain_id < 1:
            raise MisconfigurationError(f"Invalid chain id for network key: {network}")
        self._networks[network] = {
            "chain_id": chain_id,
            "tokens": {}
        }

    def add_token(self, network: str, code: str, name: str,
                  address: str, version: str,
                  decimals: int = 6, symbol: str = "",
                  default_for_symbol: bool = False):
        """
        Adds a token contract to a specific place.

        Args:
            network: The network name for which the token will be added.
            code: An internal name for this contract, like "usdc". Given
                  an existing network and a known code, adding it will
                  just use the names of the known data.
            name: A name for this contract. It may be chosen, e.g. "USDC".
            address: The address of the token.
            version: The EIP-712 version of the token. If the token is
                     an EIP-3009 token it should have a version. Try
                     "1" by default is not, or a value that is sensible
                     for the contract itself when trying.
            decimals: The amount of decimals of the token. It MUST match
                      the value returned at .decimals() in the token.
            symbol: A symbol for this contract, like $ or €. It is optional.
            default_for_symbol: Whether the current token will be resolved
                                to be the one to use when its symbol is
                                used in a price with that symbol (or no
                                symbol, perhaps).
        """

        network = network.strip().lower()
        code = code.strip().lower()
        if network not in self._networks:
            raise MisconfigurationError(f"This network is not yet set up: {network}")
        if not code:
            raise MisconfigurationError(f"Use a valid code for the token")
        if code in self._networks[network]["tokens"]:
            raise MisconfigurationError(f"This token is already set up in network {network}: {code}")
        # TODO continue implementing this.from
