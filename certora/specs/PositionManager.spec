import "./setup/SafeTransferLibCVL.spec";
import "./setup/Deltas.spec";
import "./setup/EIP712.spec";
import "./setup/PoolManager.spec";

using PositionManagerHarness as Harness;

methods {
    function getPoolAndPositionInfo(uint256 tokenId) external returns (PositionManagerHarness.PoolKey, PositionManagerHarness.PositionInfo) envfree;
    function getPoolKey(bytes32 poolId) external returns (PositionManagerHarness.PoolKey) envfree;
    function getPositionLiquidity(uint256 tokenId) external returns (uint128) envfree;
    function getPositionKeyByTokenId(uint256 tokenId) external returns (uint256) envfree;
    function Harness.poolManager() external returns (address) envfree;
    function Harness.msgSender() external returns (address) envfree;
    function getEtherBalance(address addr) external returns (uint256) envfree;
    function poolManager() external returns (address) envfree;
    function subscriber(uint256 tokenId) external returns (address) envfree;
    function getLockerSlotValue() external returns(bytes32) envfree;

    function PositionInfoLibrary.hasSubscriber(PositionManagerHarness.PositionInfo info) internal returns (bool);

    function Position.calculatePositionKey(address owner, int24 tickLower, int24 tickUpper, bytes32 salt) internal returns (bytes32) => getPositionKey(owner, tickLower, tickUpper, salt);    
    
    function Notifier._notifyModifyLiquidity(uint256 tokenId, int256 liquidityChange, PositionManagerHarness.BalanceDelta balanceDelta) internal => notifyLiquidity();
    
    // summaries for unresolved calls
    unresolved external in _._ => DISPATCH [
        PositionManagerHarness._
    ] default NONDET;
    function _.permit(address,IAllowanceTransfer.PermitSingle,bytes) external => NONDET;
    function _.permit(address,IAllowanceTransfer.PermitBatch,bytes) external => NONDET;
    function _.isValidSignature(bytes32, bytes memory) internal => NONDET;
    function _.isValidSignature(bytes32, bytes) external => NONDET;
    function _._call(address, bytes memory) internal => NONDET;
    function _._call(address, bytes) external => NONDET;
    function _.notifyUnsubscribe(uint256, PositionManagerHarness.PositionInfo, bytes) external => NONDET;
    function _.notifyUnsubscribe(uint256, PositionManagerHarness.PositionInfo memory, bytes memory) internal => NONDET;
    function _.notifyUnsubscribe(uint256) external => NONDET;
    // likely unsound, but assumes no callback
    function _.onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes data
    ) external => NONDET; /* expects bytes4 */
}

use builtin rule sanity;

ghost uint256 notifiedCounter;

function notifyLiquidity() {
    notifiedCounter = require_uint256(notifiedCounter + 1);
}

//  adding positive liquidity results in currency delta change for PositionManager
rule increaseLiquidityDecreasesBalances(env e) {
    uint256 tokenId; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; bytes hookData;
    
    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);
    require poolKey.hooks != currentContract;

    int256 delta0Before = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(poolKey.currency1, currentContract);

    // deltas must be 0 at the start of any tx
    require delta0Before == 0;
    require delta1Before == 0;

    increaseLiquidity(e, tokenId, liquidity, amount0Max, amount1Max, hookData);

    int256 delta0After = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1After = getCurrencyDeltaExt(poolKey.currency1, currentContract);

    assert liquidity != 0 => - delta0After <= require_int256(amount0Max)  && - delta1After <= require_int256(amount1Max);
}

rule increaseLiquidityIncreasesLiquidity(env e){
    uint256 tokenId; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; bytes hookData;
    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);
    require poolKey.hooks != currentContract;

    uint128 initLiquidity = getPositionLiquidity(tokenId);

    increaseLiquidity(e, tokenId, liquidity, amount0Max, amount1Max, hookData);

    assert getPositionLiquidity(tokenId) == require_uint128(initLiquidity + liquidity);
}

rule increaseLiquidityNotifySubscriber(env e){
    uint256 tokenId; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; bytes hookData;
    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);

    require notifiedCounter == 0;

    increaseLiquidity(e, tokenId, liquidity, amount0Max, amount1Max, hookData);
    
    assert notifiedCounter == 0 => !Conv.hasSubscriber(info);
    assert notifiedCounter == 1 => Conv.hasSubscriber(info);
}

// passing

rule positionManagerSanctioned(address token, method f, env e, calldataarg args) filtered {
    f -> f.selector != sig:settlePair(Conversions.Currency,Conversions.Currency).selector
    && f.selector != sig:settle(Conversions.Currency,uint256,bool).selector
    && f.selector != sig:takePair(Conversions.Currency,Conversions.Currency,address).selector
    && f.selector != sig:take(Conversions.Currency,address,uint256).selector
    && f.selector != sig:close(Conversions.Currency).selector
    && f.selector != sig:sweep(Conversions.Currency,address).selector
    && f.contract == currentContract
} {
    require e.msg.sender == msgSender(e);
    require e.msg.sender != currentContract;

    uint256 balanceBefore = balanceOfCVL(token, currentContract);
    
    f(e,args);

    uint256 balanceAfter = balanceOfCVL(token, currentContract);

    assert balanceAfter == balanceBefore;
}


rule lockerDoesntChange(method f, env e, calldataarg args) {
    address locker = msgSender(e); // calls _getLocker

    f(e,args);

    address newLocker = msgSender(e);

    assert newLocker == locker;
}

// passing
rule transferFromShouldTransferToReceiver(env e){
    address receiver; uint256 tokenId;

    require ownerOf(e, tokenId) == e.msg.sender;

    transferFrom(e, e.msg.sender, receiver, tokenId);

    assert ownerOf(e, tokenId) == receiver;
}

// passing
rule mintPositionShouldIncreaseTokenId(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    uint256 nextTokenIdBefore = nextTokenId(e);

    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    assert nextTokenId(e) == require_uint256(nextTokenIdBefore + 1);
}

rule mintPositionShouldMintToOwner(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    require msgSender(e) == owner;

    uint256 tokenId = nextTokenId(e);
    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    assert owner == 2 => ownerOf(e, tokenId) == currentContract;
    assert owner != 2 => ownerOf(e, tokenId) == owner;
}

// passing
rule mintPositionShouldCreateValidPositionInfo(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    uint256 tokenId = nextTokenId(e);

    require PoolKeyToId(getPoolKey(PoolKeyToId(key))) == PoolKeyToId(key);

    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(e, tokenId);
    
    assert PoolKeyToId(poolKey) == PoolKeyToId(key);

    assert positionInfoToBytes32(getPositionInfo(key, tickLower, tickUpper)) == positionInfoToBytes32(info);   
}   

rule mintPositionShouldSetPoolKey(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    require getPoolKey(PoolKeyToId(key)).tickSpacing == 0;

    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    assert PoolKeyToId(getPoolKey(PoolKeyToId(key))) == PoolKeyToId(key);
}

// passing
rule mintPositionShouldSetLiquidity(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    uint256 tokenId = nextTokenId(e);

    uint256 positionKey = getPositionKeyByTokenId(tokenId);
    
    require getPoolKey(PoolKeyToId(key)).tickSpacing == 0 || PoolKeyToId(getPoolKey(PoolKeyToId(key))) == PoolKeyToId(key);

    require positionKey == 0;

    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    uint128 liquidityInPool = getPositionLiquidity(tokenId);

    assert liquidityInPool >= liquidity;
}

// passing
rule mintPositionValidateAmounts(env e){
    Conversions.PoolKey key; int24 tickLower; int24 tickUpper; uint256 liquidity; uint128 amount0Max; uint128 amount1Max; address owner; bytes hookData;

    int256 delta0Before = getCurrencyDeltaExt(key.currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(key.currency1, currentContract);

    // deltas must be 0 at the start of any tx
    require delta0Before == 0;
    require delta1Before == 0;
    require key.hooks != currentContract;
  
    mintPosition(e, key, tickLower, tickUpper, liquidity, amount0Max, amount1Max, owner, hookData);

    int256 delta0After = getCurrencyDeltaExt(key.currency0, currentContract);
    int256 delta1After = getCurrencyDeltaExt(key.currency1, currentContract);

    assert require_uint256(-delta0After) <= amount0Max;
    assert require_uint256(-delta1After) <= amount1Max;
}

// passing
rule decreaseLiquidityShouldDecreaseLiquidity(env e){
    uint256 tokenId; uint128 liquidity; uint128 amount0Min; uint128 amount1Min; bytes hookData;

    uint128 initLiquidity = getPositionLiquidity(tokenId);

    decreaseLiquidity(e, tokenId, liquidity, amount0Min, amount1Min, hookData);

    assert getPositionLiquidity(tokenId) == require_uint128(initLiquidity - liquidity);
}

// passing
rule descreaseLiquidityIncreasesBalances(env e){

    uint256 tokenId; uint128 liquidity; uint128 amount0Min; uint128 amount1Min; bytes hookData;

    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);
    require poolKey.hooks != currentContract;

    int256 delta0Before = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(poolKey.currency1, currentContract); 

    require delta0Before == 0;
    require delta1Before == 0;

    decreaseLiquidity(e, tokenId, liquidity, amount0Min, amount1Min, hookData);

    int256 delta0After = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1After = getCurrencyDeltaExt(poolKey.currency1, currentContract); 

    assert liquidity != 0 => require_uint256(delta0After) >= amount0Min && require_uint256(delta1After) >= amount1Min;
}

// passing
rule burnPositionShouldMakePositionInfoZero(env e){
    uint256 tokenId; uint128 amount0Min; uint128 amount1Min; bytes hookData;

    uint128 initLiquidity = getPositionLiquidity(tokenId);

    require initLiquidity != 0;

    burnPosition(e, tokenId, amount0Min, amount1Min, hookData);

    assert getPositionKeyByTokenId(tokenId) == 0;
}

// passing
rule burnPositionShouldIncreaseBalances(env e){
    uint256 tokenId; uint128 amount0Min; uint128 amount1Min; bytes hookData;

    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);
    require poolKey.hooks != currentContract;

    int256 delta0Before = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(poolKey.currency1, currentContract); 

    require delta0Before == 0;
    require delta1Before == 0;

    uint128 liquidity = getPositionLiquidity(tokenId);

    burnPosition(e, tokenId, amount0Min, amount1Min, hookData);

    int256 delta0After = getCurrencyDeltaExt(poolKey.currency0, currentContract);
    int256 delta1After = getCurrencyDeltaExt(poolKey.currency1, currentContract); 

    assert liquidity != 0 => require_uint256(delta0After) >= amount0Min && require_uint256(delta1After) >= amount1Min; 
}

rule burnPositionShouldRemoveSubscriber(env e){
    uint256 tokenId; uint128 amount0Min; uint128 amount1Min; bytes hookData;

    address subscriberBefore = subscriber(tokenId);

    require subscriberBefore != 0;

    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;

    (poolKey, info) = getPoolAndPositionInfo(tokenId);

    require Conv.hasSubscriber(info) == true;

    burnPosition(e, tokenId, amount0Min, amount1Min, hookData);

    assert subscriber(tokenId) == 0;
}

rule validateUnsubscribe(env e){
    uint256 tokenId;
    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;
    (poolKey, info) = getPoolAndPositionInfo(tokenId);

    require Conv.hasSubscriber(info) == true;
    require subscriber(tokenId) != 0;

    unsubscribe(e, tokenId);

    assert subscriber(tokenId) == 0;
    PositionManagerHarness.PoolKey newPoolKey; PositionManagerHarness.PositionInfo newInfo;
    (newPoolKey, newInfo) = getPoolAndPositionInfo(tokenId); 

    assert Conv.hasSubscriber(newInfo) == false;
}

rule validateSubscribe(env e){
    uint256 tokenId;
    address newSubscriber;
    bytes data;

    subscribe(e, tokenId, newSubscriber, data);

    assert subscriber(tokenId) == newSubscriber;

    PositionManagerHarness.PoolKey poolKey; PositionManagerHarness.PositionInfo info;
    (poolKey, info) = getPoolAndPositionInfo(tokenId);

    assert Conv.hasSubscriber(info) == true;
}

// passed
rule settlePairShouldZeroAmount(env e){

    Conversions.Currency currency0;
    Conversions.Currency currency1;

    int256 delta0Before = getCurrencyDeltaExt(currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(currency1, currentContract); 

    address locker = msgSender(e); 

    require locker != poolManager();
    
    uint256 amount0Before = balanceOfCVL(Conv.fromCurrency(currency0), locker);
    uint256 amount1Before = balanceOfCVL(Conv.fromCurrency(currency1), locker); 

    require delta0Before < 0 && 0xffffffffffffffffffffffffffffffffffffffff >= -delta0Before;
    require delta1Before < 0 && 0xffffffffffffffffffffffffffffffffffffffff >= - delta1Before;
    require amount0Before >= -delta0Before;
    require amount1Before >= -delta1Before;

    if(Conv.fromCurrency(currency0) == 0){
        require e.msg.value == -delta0Before;
    }

    if(Conv.fromCurrency(currency1) == 0){
        require e.msg.value == -delta1Before;
    }

    settlePair(e, currency0, currency1);

    assert getCurrencyDeltaExt(currency0, currentContract) == 0;
    assert getCurrencyDeltaExt(currency1, currentContract) == 0;

    uint256 amount0After = balanceOfCVL(Conv.fromCurrency(currency0), locker);
    uint256 amount1After = balanceOfCVL(Conv.fromCurrency(currency1), locker);   
    assert Conv.fromCurrency(currency0) != 0 => amount0Before - amount0After == -delta0Before;
    assert Conv.fromCurrency(currency1) != 0 => amount1Before - amount1After == -delta1Before;  
}

// passed
rule takePairShouldIncreaseBalances(env e){
    Conversions.Currency currency0;
    Conversions.Currency currency1;

    int256 delta0Before = getCurrencyDeltaExt(currency0, currentContract);
    int256 delta1Before = getCurrencyDeltaExt(currency1, currentContract); 

    address recipient; 

    require recipient != poolManager();
    
    uint256 amount0Before = balanceOfCVL(Conv.fromCurrency(currency0), recipient);
    uint256 amount1Before = balanceOfCVL(Conv.fromCurrency(currency1), recipient); 

    require delta0Before >= 0;
    require delta1Before >= 0;

    takePair(e, currency0, currency1, recipient);

    assert getCurrencyDeltaExt(currency0, currentContract) == 0;
    assert getCurrencyDeltaExt(currency1, currentContract) == 0;

    uint256 amount0After = balanceOfCVL(Conv.fromCurrency(currency0), recipient);
    uint256 amount1After = balanceOfCVL(Conv.fromCurrency(currency1), recipient);   
    assert amount0After - amount0Before == delta0Before;
    assert amount1After - amount1Before == delta1Before;  
}

// passed
rule validateSettle(env e){

    Conversions.Currency currency;
    uint256 amount;
    bool payerIsUser;

    int256 deltaBefore = getCurrencyDeltaExt(currency, currentContract);

    address payer = payerIsUser ? msgSender(e) : currentContract;

    require payer != poolManager();

    uint256 amountToBeSettled;
    if (amount == 0){
        amountToBeSettled = require_uint256(-deltaBefore);
    }else if(amount == 0x8000000000000000000000000000000000000000000000000000000000000000){
        amountToBeSettled = balanceOfCVL(Conv.fromCurrency(currency), currentContract);
    }else{
        amountToBeSettled = amount;
    }

    uint256 balanceBefore = balanceOfCVL(Conv.fromCurrency(currency), payer);

    settle(e, currency, amount, payerIsUser);

    assert balanceOfCVL(Conv.fromCurrency(currency), payer) - balanceBefore == amountToBeSettled;
}

// passed
rule validateTake(env e){
    Conversions.Currency currency;
    address recipient;
    uint256 amount;
    address receiver = recipient;
    uint256 amountToReceive = amount;
    if(recipient == 1){
        receiver = msgSender();
    }else if(recipient == 2){
        receiver = currentContract;
    }

    if(amount == 0){
        int256 amountDelta = getCurrencyDeltaExt(currency, currentContract);
        require amountDelta > 0;
        amountToReceive = require_uint256(amountDelta);
    }

    require receiver != poolManager();

    uint256 preBalance = balanceOfCVL(Conv.fromCurrency(currency), receiver);

    take(e, currency, recipient, amount);

    uint256 postBalance = balanceOfCVL(Conv.fromCurrency(currency), receiver);

    assert postBalance - preBalance == amountToReceive;
}

// passed, recheck
rule validateClose(env e){

    Conversions.Currency currency;

    int256 delta = getCurrencyDeltaExt(currency, currentContract);

    require delta < 0 && 0xffffffffffffffffffffffffffffffffffffffff >= -delta;

    address caller = msgSender();

    require caller != poolManager();

    uint256 balanceBefore = balanceOfCVL(Conv.fromCurrency(currency), caller);

    if(Conv.fromCurrency(currency) == 0 && delta < 0){
        require e.msg.value == -delta;
    }

    close(e, currency);

    uint256 balanceAfter = balanceOfCVL(Conv.fromCurrency(currency), caller);

    assert delta > 0 => balanceAfter - balanceBefore == delta;
    assert delta < 0 && Conv.fromCurrency(currency) != 0 => balanceBefore - balanceAfter == -delta;
}

// passed
rule validateClearOrTake(env e){
    Conversions.Currency currency;
    uint256 amountMax;

    int256 delta = getCurrencyDeltaExt(currency, currentContract);

    address recipient = msgSender();

    require recipient != poolManager();

    uint256 balanceBefore = balanceOfCVL(currency, recipient);

    clearOrTake(e, currency, amountMax);

    assert delta > amountMax => balanceOfCVL(currency, recipient) - balanceBefore == delta;
    assert getCurrencyDeltaExt(currency, currentContract) == 0;
}

// passed
rule validateSweep(env e){
    Conversions.Currency currency;
    address to;

    address receiver = to;
    if(to == 1){
        receiver = msgSender();

        bytes32 lockerValue = getLockerSlotValue();

        require lockerValue == to_bytes32(receiver);
    }else if(to == 2){
        receiver = currentContract;
    }

    uint256 balanceBefore = Conv.fromCurrency(currency) == 0 ? getEtherBalance(receiver) : balanceOfCVL(Conv.fromCurrency(currency), receiver);

    uint256 balance = Conv.fromCurrency(currency) == 0 ? getEtherBalance(currentContract) : balanceOfCVL(Conv.fromCurrency(currency), currentContract);

    sweep(e, currency, to);

    uint256 balanceAfter = Conv.fromCurrency(currency) == 0 ? getEtherBalance(receiver) : balanceOfCVL(Conv.fromCurrency(currency), receiver); 

    assert receiver != currentContract => balanceAfter - balanceBefore == balance;
}