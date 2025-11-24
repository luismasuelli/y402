# y402
An improvement over x402 protocol, and some convenience libraries

## y402 extensions over x402

### X-Payment-Networks header

The `X-Payment-Networks` contains a Base64-encoded mapping `name => chain_id`. This is optional, and not found on x402.
A y402 client can detect this header to have info of additional networks used by the server. Otherwise, it resorts to
the networks it knows (when mapping the chain id from the network name inside a payment).
