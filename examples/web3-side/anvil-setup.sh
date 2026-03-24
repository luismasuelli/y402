TEMP_FILE_STDOUT=$(mktemp)
TEMP_FILE_STDERR=$(mktemp)

# Deployer of the ERC-20/ERC-3009 contract.
ANVIL_ACC0_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
ANVIL_ACC0_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# Buyer data. Can be overridden by command line.
ANVIL_ACC1_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
ANVIL_ACC1_ADDRESS=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
TARGET_ADDRESS=${1:-$ANVIL_ACC1_ADDRESS}

# Launch anvil, wait 5 seconds, and send 10 ETH to the target address.
echo "1. Launching anvil (background)..."
anvil &
ANVIL_PID=$!
echo "2. Waiting a while..."
sleep 2
echo "3. Deploying the USD Fake contract..."
forge script script/USDFake.s.sol --private-key=$ANVIL_ACC0_PRIVATE_KEY --broadcast --rpc-url http://localhost:8545
CONTRACT_ADDRESS=$(cat broadcast/USDFake.s.sol/31337/run-latest.json | jq -r .transactions[0].contractAddress)
echo "4. Sending tokens to the buyer..."
cast send $CONTRACT_ADDRESS "transfer(address,uint256)" $TARGET_ADDRESS 1000000000000 --rpc-url http://localhost:8545 --private-key=$ANVIL_ACC0_PRIVATE_KEY
echo "   >>> Contract Address is: $CONTRACT_ADDRESS"
echo "5. Use the following setup for fake_facilitator.py:"
echo "   - FACILITATOR_TOKEN_ADDRESS=$CONTRACT_ADDRESS"
echo "   Use the following setup for payment_api.py:"
echo "   - SERVER_TOKEN_ADDRESS=$CONTRACT_ADDRESS"
echo "   - SERVER_INTERNAL_CLIENT_LIBRARY=httpx, httpx_sync or requests (Flask one does not support httpx)"
echo "   Use the following setup for worker.py:"
echo "   - WORKER_INTERNAL_CLIENT_LIBRARY=httpx, httpx_sync pr requests"
echo "   - WORKER_WEBHOOK_NAME={dynamic|fixed}_type_{fastapi|flask}"
echo "   - WORKER_WEBHOOK_URL=/api/webhook/payments{1|2|3}"
echo "5. Joining anvil..."
echo
echo
echo
wait $ANVIL_PID
