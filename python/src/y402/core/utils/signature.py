from eth_account import Account
from eth_account.messages import encode_typed_data
from ...core.types.client import EIP3009Authorization


def check_signature(
    name: str, version: str, chain_id: int, asset: str,
    authorization: EIP3009Authorization, signature: str
):
    """
    Checks that a given payment authorization is OK
    related to the signature itself and the provided
    complementary data related to the token.
    :param name: The name of the token.
    :param version: The version of the token.
    :param chain_id: The chain id of the token.
    :param asset: The address of the token.
    :param authorization: The authorization.
    :param signature: The signature.
    :return: Whether all that data matches.
    """

    typed_data = {
        "types": {
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ]
        },
        "primaryType": "TransferWithAuthorization",
        "domain": {
            "name": name, "version": version,
            "chainId": chain_id, "verifyingContract": asset
        },
        "message": {
            "from": authorization.from_,
            "to": authorization.to,
            "value": authorization.value,
            "validAfter": authorization.valid_after,
            "validBefore": authorization.valid_before,
            "nonce": authorization.nonce,
        }
    }

    # Reconstruct the sign-able data out of the types data
    # and also check the signature completely.
    sign_able = encode_typed_data(
        domain_data=typed_data["domain"],
        message_types=typed_data["types"],
        message_data=typed_data["message"],
    )
    recovered_address = Account.recover_message(
        sign_able, signature=signature
    )
    return recovered_address.lower() == authorization.from_.lower()
