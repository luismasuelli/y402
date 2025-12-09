# Web3-side examples

For this example, this is the web3 side: a generic contract serving ERC-3009 purposes as well.
This project requires [Foundry](https://getfoundry.sh/) to be installed, and it's only purpose
is to have a dumb token to play with for the purpose of x402 (y402) protocol.

## Installation

This is easy and pretty much standard for a Foundry project:

1. Have Foundry installed (this example uses: `forge`, `anvil`, `cast`). The default setup (i.e.
   not needed to use the ZK setup or so).

2. Launch `anvil`: Rather than doing this process directly, we'll use a convenience script
   coming with the example and leveraging the power of the fake accounts that come with
   fake money (we'll use 4 different accounts for this purpose):

   ```shell
   ./anvil-setup.sh
   ```

3. Launch the other components of this example (servers, workers, clients).
