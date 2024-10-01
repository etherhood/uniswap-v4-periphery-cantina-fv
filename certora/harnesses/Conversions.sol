// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.24;

import { Currency } from "@uniswap/v4-core/src/types/Currency.sol";
import { BalanceDeltaLibrary, BalanceDelta } from "@uniswap/v4-core/src/types/BalanceDelta.sol";
import { PositionConfig } from "src/libraries/PositionConfig.sol";
import {PositionInfo, PositionInfoLibrary} from "src/libraries/PositionInfoLibrary.sol";
import { PoolKey } from "@uniswap/v4-core/src/types/PoolKey.sol";
import { PoolId } from "@uniswap/v4-core/src/types/PoolId.sol";
import {BalanceDelta} from "@uniswap/v4-core/src/types/BalanceDelta.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";

contract Conversions {
    function hashConfigElements(
        Currency currency0,
        Currency currency1,
        uint24 fee,
        int24 tickSpacing,
        address hooks,
        int24 tickLower,
        int24 tickUpper
    ) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(currency0, currency1, fee, tickSpacing, hooks, tickLower, tickUpper));
    }

    function wrapToPoolId(bytes32 _id) public pure returns (PoolId) {
        return PoolId.wrap(_id);
    }

    function fromCurrency(Currency currency) public pure returns (address) {
        return Currency.unwrap(currency);
    }

    function toCurrency(address token) public pure returns (Currency) {
        return Currency.wrap(token);
    }

    function amount0(BalanceDelta balanceDelta) external pure returns (int128) {
        return BalanceDeltaLibrary.amount0(balanceDelta);
    }

    function amount1(BalanceDelta balanceDelta) external pure returns (int128) {
        return BalanceDeltaLibrary.amount1(balanceDelta);
    }

    function poolKeyToId(PoolKey memory poolKey) public pure returns (bytes32) {
        return keccak256(abi.encode(poolKey));
    }
    
    function positionKey(address owner, int24 tickLower, int24 tickUpper, bytes32 salt) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(owner, tickLower, tickUpper, salt));
    }

    function positionInfoToBytes32(PositionInfo info) public pure returns (bytes32) {
        return bytes32(PositionInfo.unwrap(info));
    }

    function getPositionInfo(PoolKey memory poolKey, int24 tickLower, int24 tickUpper) public pure returns (PositionInfo) {
        return PositionInfoLibrary.initialize(poolKey, tickLower, tickUpper);
    }

    function hasSubscriber(PositionInfo info) public pure returns (bool) {
        return PositionInfoLibrary.hasSubscriber(info);
    }

    function getPoolId(
        Currency currency0, 
        Currency currency1, 
        int24 tickSpacing,
        uint24 fee,
        address hooks
    ) external view returns (bytes32){
        (currency0, currency1) = currency0 < currency1 ? (currency0, currency1) : (currency1, currency0);
        return poolKeyToId(PoolKey(currency0, currency1, fee, tickSpacing, IHooks(hooks))); 
    }
}