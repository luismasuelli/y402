# y402
An improvement over x402 protocol, and some convenience libraries. This version covers improvements
over x402 V1 only.

In order to understand what x402 is, take a look at the [official documentation](https://docs.cdp.coinbase.com/x402/welcome).
Since this version covers V1 only (and the documentation uses V2), take also a look to [this page](https://docs.cdp.coinbase.com/x402/migration-guide#migration-guide-v1-v2)
to understand how V1 was.

On top of what V1 is, as protocol implementation, y402 improves the following:

1. The way to install it in your own server is different to the official packages. This
   relates to the extra features supported here (e.g. dynamic prices based on analyzing
   the current incoming request).
2. There are extra features which make the server-side flow slightly different, adding
   the notion of webhooks (similar to well-known payment providers) that are accessed
   but out-of-the-box workers that process the incoming payments (the request itself
   should not handle the payment, but it can to some extent). For example, there's a
   notion of storing and debugging the payments, while having them ready to send them
   to appropriate webhooks.
3. There are extra features, both in the client and the server, to aid in the networks
   synchronization between the client and the server (such feature is only leveraged
   when both the client and server use this y402 library).

Other than that, this implementation is -protocol-wide- completely compatible with V1.

## Python package

Read the Python documentation [here](python/README.md).

## y402 extensions over x402

These are the protocol extensions over y402.

### X-Payment-Networks response header

The `X-Payment-Networks` header contains a Base64-encoded mapping `name => chain_id`. This is optional, and not found
on x402. A y402 client can detect this header to have info of additional networks used by the server. Otherwise, it 
resorts to the networks it knows (when mapping the chain id from the network name inside a payment).

### X-Payment-Asset request header

The `X-Payment-Asset` header contains the address of the intended asset. This is useful but optional (just adding the
signature will be interpreted in an iteration to determine the selected asset) but ensures consistency. A y402 server
will understand this header and perform the double check. A x402 server will not be aware of it.