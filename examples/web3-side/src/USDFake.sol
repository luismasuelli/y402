// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// @title USD Fake (USDF) - ERC20 + EIP-712 + ERC-3009 test token
/// @notice NOT FOR PRODUCTION USE
contract USDFake is ERC20, EIP712 {
    // --- ERC-3009 types / state -------------------------------------------------

    /// @dev Authorization state as in EIP-3009
    enum AuthorizationState {
        Unused,
        Used,
        Canceled
    }

    /// @dev authorizer => nonce => state
    mapping(address => mapping(bytes32 => AuthorizationState)) private _authorizationStates;

    /// @notice Emitted when an authorization is used
    event AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce);

    /// @notice Emitted when an authorization is canceled
    event AuthorizationCanceled(address indexed authorizer, bytes32 indexed nonce);

    /// @notice EIP-712 typehash for TransferWithAuthorization
    bytes32 public constant TRANSFER_WITH_AUTHORIZATION_TYPEHASH =
    keccak256(
        "TransferWithAuthorization("
        "address from,"
        "address to,"
        "uint256 value,"
        "uint256 validAfter,"
        "uint256 validBefore,"
        "bytes32 nonce"
        ")"
    );

    /// @notice EIP-712 typehash for ReceiveWithAuthorization
    bytes32 public constant RECEIVE_WITH_AUTHORIZATION_TYPEHASH =
    keccak256(
        "ReceiveWithAuthorization("
        "address from,"
        "address to,"
        "uint256 value,"
        "uint256 validAfter,"
        "uint256 validBefore,"
        "bytes32 nonce"
        ")"
    );

    /// @notice EIP-712 typehash for CancelAuthorization
    bytes32 public constant CANCEL_AUTHORIZATION_TYPEHASH =
    keccak256(
        "CancelAuthorization("
        "address authorizer,"
        "bytes32 nonce"
        ")"
    );

    // --- Constructor ------------------------------------------------------------

    /// @param initialSupply Initial mint to msg.sender (in smallest units, 6 decimals)
    constructor(uint256 initialSupply)
    ERC20("USD Fake", "USDF")
    EIP712("USD Fake", "1") // EIP-712 domain: name = "USD Fake", version = "1"
    {
        _mint(msg.sender, initialSupply);
    }

    // --- ERC-20 overrides -------------------------------------------------------

    /// @notice Use 6 decimals.
    function decimals() public pure override returns (uint8) {
        return 6;
    }

    // --- EIP-712 helpers --------------------------------------------------------

    /// @notice Expose domain separator for tooling that expects it on-chain.
    function DOMAIN_SEPARATOR() external view returns (bytes32) {
        return _domainSeparatorV4();
    }

    // --- ERC-3009 view ----------------------------------------------------------

    /// @notice Get current authorization state for (authorizer, nonce)
    function authorizationState(address authorizer, bytes32 nonce)
    external
    view
    returns (AuthorizationState)
    {
        return _authorizationStates[authorizer][nonce];
    }

    // --- Modifiers / internal helpers -------------------------------------------

    modifier onlyValidTimeframe(uint256 validAfter, uint256 validBefore) {
        // EIP-3009: validAfter is exclusive, validBefore is exclusive
        require(block.timestamp > validAfter, "USDF: authorization not yet valid");
        require(block.timestamp < validBefore, "USDF: authorization expired");
        _;
    }

    function _useAuthorization(address authorizer, bytes32 nonce) internal {
        AuthorizationState state = _authorizationStates[authorizer][nonce];
        require(state == AuthorizationState.Unused, "USDF: authorization not unused");

        _authorizationStates[authorizer][nonce] = AuthorizationState.Used;
        emit AuthorizationUsed(authorizer, nonce);
    }

    function _cancelAuthorizationInternal(address authorizer, bytes32 nonce) internal {
        AuthorizationState state = _authorizationStates[authorizer][nonce];
        require(state == AuthorizationState.Unused, "USDF: authorization cannot be canceled");

        _authorizationStates[authorizer][nonce] = AuthorizationState.Canceled;
        emit AuthorizationCanceled(authorizer, nonce);
    }

    function _recoverAuthorizationSigner(bytes32 structHash, bytes memory signature)
    internal
    view
    returns (address)
    {
        bytes32 digest = _hashTypedDataV4(structHash);
        return ECDSA.recover(digest, signature);
    }

    // --- ERC-3009 core functions -----------------------------------------------

    /// @notice Execute a transfer with a signed authorization (EIP-3009)
    /// @param from        Payer (authorizer)
    /// @param to          Payee
    /// @param value       Amount to transfer
    /// @param validAfter  Time after which this is valid (unix timestamp)
    /// @param validBefore Time before which this is valid (unix timestamp)
    /// @param nonce       Unique 32-byte nonce
    /// @param signature   ECDSA signature over EIP-712 typed data
    function transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        bytes calldata signature
    ) external onlyValidTimeframe(validAfter, validBefore) {
        bytes32 structHash = keccak256(
            abi.encode(
                TRANSFER_WITH_AUTHORIZATION_TYPEHASH,
                from,
                to,
                value,
                validAfter,
                validBefore,
                nonce
            )
        );

        address signer = _recoverAuthorizationSigner(structHash, signature);
        require(signer == from, "USDF: invalid signature");

        _useAuthorization(from, nonce);
        _transfer(from, to, value);
    }

    /// @notice Safer pull-style transfer with signed authorization (EIP-3009)
    /// @dev Requires msg.sender == `to` to prevent front-running
    function receiveWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        bytes calldata signature
    ) external onlyValidTimeframe(validAfter, validBefore) {
        require(msg.sender == to, "USDF: caller must be payee");

        bytes32 structHash = keccak256(
            abi.encode(
                RECEIVE_WITH_AUTHORIZATION_TYPEHASH,
                from,
                to,
                value,
                validAfter,
                validBefore,
                nonce
            )
        );

        address signer = _recoverAuthorizationSigner(structHash, signature);
        require(signer == from, "USDF: invalid signature");

        _useAuthorization(from, nonce);
        _transfer(from, to, value);
    }

    /// @notice Cancel an unused authorization (EIP-3009)
    /// @param authorizer The address that originally signed the authorization
    /// @param nonce      The nonce of the authorization
    /// @param signature  Signature of `authorizer` over the CancelAuthorization struct
    function cancelAuthorization(
        address authorizer,
        bytes32 nonce,
        bytes calldata signature
    ) external {
        bytes32 structHash = keccak256(
            abi.encode(
                CANCEL_AUTHORIZATION_TYPEHASH,
                authorizer,
                nonce
            )
        );

        address signer = _recoverAuthorizationSigner(structHash, signature);
        require(signer == authorizer, "USDF: invalid signature");

        _cancelAuthorizationInternal(authorizer, nonce);
    }
}