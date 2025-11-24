# y402
An improvement over x402 protocol, and some convenience libraries

## y402 extensions over x402

### X-Payment-Networks response header

The `X-Payment-Networks` header contains a Base64-encoded mapping `name => chain_id`. This is optional, and not found
on x402. A y402 client can detect this header to have info of additional networks used by the server. Otherwise, it 
resorts to the networks it knows (when mapping the chain id from the network name inside a payment).

### X-Payment-Asset request header

The `X-Payment-Asset` header contains the address of the intended asset. This is useful but optional (just adding the
signature will be interpreted in an iteration to determine the selected asset) but ensures consistency. A y402 server
will understand this header and perform the double check. A x402 server will not be aware of it.