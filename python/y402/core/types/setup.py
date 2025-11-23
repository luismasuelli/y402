from typing import Tuple, Optional, List, Dict
from decimal import Decimal
from .errors import MisconfigurationError
from .default_data import KNOWN_NETWORKS_AND_TOKENS


class Y402Setup:
    """
    A setup tells in a set of internal mappings:

    - The available networks.
    - The tokens in those networks.
    """

    def __init__(self):
        self._networks = {}
        self._default_tokens = {}

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
        if network in KNOWN_NETWORKS_AND_TOKENS and chain_id < 1:
            chain_id = KNOWN_NETWORKS_AND_TOKENS[network]["chain_id"]
        if chain_id < 1:
            raise MisconfigurationError(f"Invalid chain id for network key: {network}")
        self._networks[network] = {
            "chain_id": chain_id,
            "tokens": {},
            "tokens_by_address": {},
            "default_token": None
        }

    def add_token(self, network: str, code: str,
                  # The name.
                  name: str = "",
                  # The address and the version.
                  address: str = "", version: str = "",
                  # The decimals and the symbol.
                  decimals: int = 0, symbol: str = "",
                  # Whether it's default or not.
                  default_for_symbol: bool = False):
        """
        Adds a token contract to a specific place.

        Args:
            network: The network name for which the token will be added.
            code: An internal name for this contract, like "usdc". Given
                  an existing network and a known code, adding it will
                  just use the names of the known data, optionally with
                  some overrides (e.g. the version).
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
        if symbol in " 0123456789." or len(symbol) > 1:
            raise MisconfigurationError(f"Invalidd symbol: {symbol}")

        if code in KNOWN_NETWORKS_AND_TOKENS[network]["tokens"]:
            known_token = KNOWN_NETWORKS_AND_TOKENS[network]["tokens"][code]
            decimals = decimals or known_token["decimals"]
            version = version or known_token["eip712Version"]
            symbol = symbol or known_token["symbol"]
            address = address or known_token["address"]
            name = name or known_token["name"]

        name = name.strip() or code.upper()
        if not address or not version or decimals < 0 or not name:
            raise MisconfigurationError(f"One or more token arguments are missing")
        if address in self._networks[network]["tokens_by_address"]:
            raise MisconfigurationError(f"This token's address is already setup in network {network}: {address}")

        self._networks[network]["tokens"][code] = {
            "name": name, "symbol": symbol, "address": address,
            "version": version, "decimals": decimals
        }
        self._networks[network]["tokens_by_address"][address] = code
        if default_for_symbol:
            self._default_tokens.setdefault(network, {})[symbol] = code

    def _check_network_and_code(self, network: str, code: str) -> Tuple[str, str]:
        """
        Checks the chosen network and token code to exist.

        Args:
            network: The network name for which the token will be added.
            code: An internal name for an existing token contract in the
                  network in this setup.
        """

        network = network.strip().lower()
        code = code.strip().lower()
        if network not in self._networks:
            raise MisconfigurationError(f"This network is not yet set up: {network}")
        if not code:
            raise MisconfigurationError(f"Use a valid code for the token")
        if code not in self._networks[network]["tokens"]:
            raise MisconfigurationError(f"This token is not yet set up in network {network}: {code}")

        return network, code

    def set_default_for_symbol_token(self, network: str, code: str):
        """
        Given a network code and a token code, it ensures the token
        becomes the default one for its symbol (even if for some
        reason no symbol were to be defined in a token).

        Args:
            network: The network name for which the token will be added.
            code: An internal name for an existing token contract in the
                  network in this setup.
        """

        network, code = self._check_network_and_code(network, code)
        token = self._networks[network]["tokens"][code]
        symbol = token["symbol"]
        self._default_tokens[network][symbol] = code

    def set_default_token(self, network: str, code: str):
        """
        Given a network code and a token code, it ensures the token
        becomes the default one, this time not for its symbol but
        instead for when an integer value is used.

        Args:
            network: The network name for which the token will be defaulted.
            code: An internal name for an existing token contract in the
                  network in this setup.
        """

        network, code = self._check_network_and_code(network, code)
        self._networks[network]["default_token"] = code

    def get_default_token(self, network: str) -> Optional[str]:
        """
        Gets the default token of a network

        Args:
            network: The network name for which the token will be defaulted.
        Returns:
            The default token code of that network.
        """

        return self._networks[network]["default_token"]

    def _get_price_label(self, value: str, decimals: int, symbol: str):
        """
        Builds a price label for an amount of a given currency.

        Args:
            value: A decimal representation of the amount.
            decimals: The amount of digits that are decimal places.
            symbol: The currency symbol.
        Returns:
            A textual representation.
        """

        d = Decimal(value) / (10 ** decimals)
        return f"{symbol}{d}"

    def list_tokens(self, network: str) -> List[str]:
        """
        Returns the list of registered token (codes) for a network.

        Args:
            network: The network name for which the tokens will be listed.
        Returns:
            The list of registered tokens.
        """

        network = network.strip().lower()
        if network not in self._networks:
            raise MisconfigurationError(f"This network is not yet set up: {network}")
        return list(self._networks[network]["tokens"].keys())

    def get_token_metadata(self, network: str, code: str) -> Tuple[str, str, str, str, int]:
        """
        Returns the metadata associated to a token.

        Args:
            network: The network name for which the token will be defaulted.
            code: An internal name for an existing token contract in the
                  network in this setup.
        Returns:
            The associated metadata.
        """

        network, code = self._check_network_and_code(network, code)
        token = self._networks[network]["tokens"][code]
        return token["name"], token["symbol"], token["address"], token["version"], token["decimals"]

    def get_payment_data(self, network: str, token: str, value: str) -> tuple[int, str, str, str]:
        """
        Returns data associated to a specific token payment.

        Args:
            network: The name of the network.
            token: The address of the token contract.
            value: A decimal representation of the amount.
        Returns:
            A tuple (chain_id, code, name, price_label).
        """

        network = network.strip().lower()
        if network not in self._networks:
            raise MisconfigurationError(f"This network is not yet set up: {network}")
        if token not in self._networks[network]["tokens_by_address"]:
            raise MisconfigurationError(f"Use a valid code for the token")
        code = self._networks[network]["tokens_by_address"][token]
        token_data = self._networks[network]["tokens"]
        decimals = token_data["decimals"]
        name = token_data["name"]
        chain_id = self._networks[network]["chain_id"]
        symbol = token_data["symbol"]
        return chain_id, code, name, self._get_price_label(value, decimals, symbol)

    def get_chain_id(self, network: str) -> int:
        """
        Given a network, returns its chain id.

        Args:
            network: The name of the network.
        Returns:
            An integer being the chain id.
        """

        try:
            return self._networks[network]["chain_id"]
        except:
            raise MisconfigurationError(f"This network is not set up: {network}")

    def get_chain_ids_mapping(self) -> Dict[str, int]:
        """
        Returns the available mapping of name => chain_id.

        Returns:
            A dictionary mapping name => chain_id from this setup.
        """

        return {key: value["chain_id"] for key, value in self._networks.items()}

    def parse_price_label(self, network: str, label: str) -> tuple[str, str]:
        """
        Given a price label, it tries to parse it.

        Args:
            network: The name of the network.
            label: The label to parse.
        Returns:
            The parsed token price, as (asset address, amount).
        """

        label = label.strip()
        if not label:
            return "", "0"

        # 1. Parse the symbol and get the token.
        if label[0] not in "0123456789.":
            symbol, price = label[0], label[1:]
        else:
            symbol, price = "", label
        if symbol not in self._default_tokens[network]:
            raise MisconfigurationError(f"The symbol '{symbol}' is not default-registered in network: {network}")
        code = self._default_tokens[network][symbol]
        token_data = self._networks[network]["tokens"][code]
        token = token_data["address"]
        decimals = token_data["decimals"]

        # 2. Parse the price and multiply by decimals to get the amount.
        try:
            d = Decimal(price)
            if d < 0:
                raise ValueError("Invalid Price")
            amount = str(int(d * 10 ** decimals))
        except:
            raise MisconfigurationError(f"The price '{price} is not a valid amount")

        # 3. Return both.
        return token, amount

    def __or__(self, other: 'Y402Setup'):
        """
        Merges two definitions (as a new definition) when doing this. The
        definitions in the first operand take precedence when defining
        networks and tokens, but the definitions in the second operand
        take precedence when defining defaults.
        :param other: The other setup to merge.
        :return: The new, merged, definition.
        """

        if not isinstance(other, Y402Setup):
            raise TypeError(f"Can only merge Y402Setup (not \"{type(other).__name__}\") to Y402Setup")

        merged = Y402Setup()
        for obj in [self, other]:
            for network, values in obj._networks.items():
                # First, add the network.
                chain_id = values["chain_id"]
                tokens = values["tokens"]
                try:
                    merged.add_network(network, chain_id)
                except:
                    pass

                # Then, add the tokens.
                for code, token_data in tokens.items():
                    name = token_data["name"]
                    symbol = token_data["symbol"]
                    address = token_data["address"]
                    version = token_data["version"]
                    decimals = token_data["decimals"]
                    try:
                        obj.add_token(network, code, name, address, version, decimals, symbol)
                    except:
                        pass

                # Finally, add the defaults. The defaults
                # in the other setup will take precedence.
                for symbol, code in obj._default_tokens.get(network, {}):
                    merged.set_default_for_symbol_token(network, code)

        return merged
