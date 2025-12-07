// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Script} from "forge-std/Script.sol";
import {USDFake} from "../src/USDFake.sol";

contract USDFakeScript is Script {
    USDFake public counter;

    function setUp() public {}

    function run() public {
        vm.startBroadcast();
        counter = new USDFake(1000000_000000);
        vm.stopBroadcast();
    }
}
