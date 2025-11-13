from decimal import Decimal
from y402.core.types.errors import MisconfigurationError


KNOWN_DATA = {
    "base": {
        "chain_id": 8453,
        "tokens": {
            "usdc": {
                "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            },
            "eurc": {
                "address": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42",
                "name": "EUR Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "€"
            }
        }
    },
    "base-sepolia": {
        "chain_id": 84532,
        "tokens": {
            "usdc": {
                "address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            },
            "eurc": {
                "address": "0x808456652fdb597867f38412077A9182bf77359F",
                "name": "EUR Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "€"
            }
        }
    },
    "avalanche": {
        "chain_id": 43114,
        "tokens": {
            "usdc": {
                "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            },
            "eurc": {
                "address": "0xc891eb4cbdeff6e073e859e987815ed1505c2acd",
                "name": "EUR Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "€"
            }
        }
    },
    "avalanche-fuji": {
        "chain_id": 43113,
        "tokens": {
            "usdc": {
                "address": "0x5425890298aed601595a70AB815c96711a31Bc65",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            },
            "eurc": {
                "address": "0x5E44db7996c682E92a960b65AC713a54AD815c6B",
                "name": "EUR Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "€"
            }
        }
    },
    "sei": {
        "chain_id": 1329,
        "tokens": {
            "usdc": {
                "code": "usdc",
                "address": "0xe15fC38F6D8c56aF07bbCBe3BAf5708A2Bf42392",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            }
        }
    },
    "sei-testnet": {
        "chain_id": 1328,
        "tokens": {
            "usdc": {
                "code": "usdc",
                "address": "0x4fCF1784B31630811181f670Aea7A7bEF803eaED",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            }
        }
    },
    "polygon": {
        "chain_id": 137,
        "tokens": {
            "usdc": {
                "code": "usdc",
                "address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            }
        }
    },
    "polygon-amoy": {
        "chain_id": 80002,
        "tokens": {
            "usdc": {
                "code": "usdc",
                "address": "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582",
                "name": "USD Coin",
                "decimals": 6,
                "eip712Version": "2",
                "symbol": "$"
            }
        }
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
        if network in KNOWN_DATA and chain_id < 1:
            chain_id = KNOWN_DATA[network]["chain_id"]
        if chain_id < 1:
            raise MisconfigurationError(f"Invalid chain id for network key: {network}")
        self._networks[network] = {
            "chain_id": chain_id,
            "tokens": {},
            "tokens_by_address": {}
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

        if code in KNOWN_DATA[network]["tokens"]:
            known_token = KNOWN_DATA[network]["tokens"][code]
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

        network = network.strip().lower()
        code = code.strip().lower()
        if network not in self._networks:
            raise MisconfigurationError(f"This network is not yet set up: {network}")
        if not code:
            raise MisconfigurationError(f"Use a valid code for the token")
        if code not in self._networks[network]["tokens"]:
            raise MisconfigurationError(f"This token is not yet set up in network {network}: {code}")

        token = self._networks[network]["tokens"][code]
        symbol = token["symbol"]
        self._default_tokens[network][symbol] = code

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

    def get_token_data(self, network: str, token: str, value: str) -> tuple[int, str, str, str]:
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
