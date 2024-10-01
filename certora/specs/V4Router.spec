import "./setup/PoolManager.spec";

using V4RouterHarness as Harness;

methods {
    // envfree
    function Harness.msgSender() external returns (address) envfree;
    function Harness.getEtherBalance(address addr) external returns (uint256) envfree;

    // summaries for unresolved calls
    unresolved external in _._ => DISPATCH [
        V4RouterHarness._
    ] default NONDET;
    function _.permit(address,IAllowanceTransfer.PermitSingle,bytes) external => NONDET;
    function _.permit(address,IAllowanceTransfer.PermitBatch,bytes) external => NONDET;
    function _.isValidSignature(bytes32, bytes memory) internal => NONDET;
    function _.isValidSignature(bytes32, bytes) external => NONDET;
    function _._call(address, bytes memory) internal => NONDET;
    function _._call(address, bytes) external => NONDET;
    function _.notifyUnsubscribe(uint256, V4RouterHarness.PositionConfig, bytes) external => NONDET;
    function _.notifyUnsubscribe(uint256, V4RouterHarness.PositionConfig memory, bytes memory) internal => NONDET;
    // likely unsound, but assumes no callback
    function _.onERC721Received(
        address operator,
        address from,
        uint256 tokenId,
        bytes data
    ) external => NONDET; /* expects bytes4 */
}

use builtin rule sanity filtered { f -> f.contract == currentContract }

// passed
rule swapExactInShouldNotUserMoreThanAmountIn(env e){

    IV4Router.ExactInputParams params;

    int256 deltaBefore = getCurrencyDeltaExt(params.currencyIn, currentContract);

    uint256 amountIn = params.amountIn == 0 ? require_uint256(deltaBefore) : params.amountIn;

    require params.path.length == 1 && params.path[0].hooks != currentContract;

    swapExactIn(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(params.currencyIn, currentContract);

    assert require_int256(deltaBefore - deltaAfter) <= amountIn && require_int256(deltaBefore - deltaAfter) >= 0; 
}

// passed
rule swapExactInShouldValidateAmountOut(env e){

    IV4Router.ExactInputParams params;

    uint256 lastIndex = require_uint256(params.path.length - 1);

    // Conv.Currency currencyOut = params.path[lastIndex].intermediateCurrency;

    int256 deltaBefore = getCurrencyDeltaExt(params.path[lastIndex].intermediateCurrency, currentContract);

    require params.path[lastIndex].hooks != currentContract;

    swapExactIn(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(params.path[lastIndex].intermediateCurrency, currentContract);

    assert params.path[lastIndex].intermediateCurrency != params.currencyIn => require_int128(deltaAfter - deltaBefore) >= params.amountOutMinimum; 
}

rule swapExactInShouldCallAllPools(env e){

    IV4Router.ExactInputParams params;

    require calls == 0;

    uint256 length = require_uint256(params.path.length);

    require length > 1;

    swapExactIn(e, params);

    assert calls == length; 
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

// passed
rule swapExactInSingleShouldNotUseMoreAmountIn(env e){

    IV4Router.ExactInputSingleParams params;

    Conversions.Currency currencyIn = params.zeroForOne ? params.poolKey.currency0 : params.poolKey.currency1;

    int256 deltaBefore = getCurrencyDeltaExt(currencyIn, currentContract);

    uint256 amountIn = params.amountIn == 0 ? require_uint256(deltaBefore) : params.amountIn;

    require params.poolKey.hooks != currentContract;

    swapExactInSingle(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyIn, currentContract);

    assert require_int256(deltaBefore - deltaAfter) <= amountIn && require_int256(deltaBefore - deltaAfter) >= 0;
}

// passed
rule ruleExactInSingleShouldValidateAmountOut(env e){

    IV4Router.ExactInputSingleParams params;

    Conversions.Currency currencyOut = params.zeroForOne ? params.poolKey.currency1 : params.poolKey.currency0;

    int256 deltaBefore = getCurrencyDeltaExt(currencyOut, currentContract);

    require params.poolKey.hooks != currentContract;

    swapExactInSingle(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyOut, currentContract);

    assert require_int256(deltaAfter - deltaBefore) >= params.amountOutMinimum;
}

rule swapExactInSingleShoultNotExceedPriceLimit(env e){
    IV4Router.ExactInputSingleParams params;

    require params.poolKey.hooks != currentContract;

    swapExactInSingle(e, params);

    uint160 price = poolSqrtPriceX96[PoolKeyToId(params.poolKey)];

    uint160 limitPrice;
    if(params.sqrtPriceLimitX96 == 0){
        limitPrice = params.zeroForOne ? 4295128739 + 1 : 1461446703485210103287273052203988822378723970342 - 1;
    }else{
        limitPrice = params.sqrtPriceLimitX96;
    }

    assert params.zeroForOne ? price >= limitPrice : price <= limitPrice;
}

// passed
rule swapExactOutputSingleIncreaseTokenOutBalance(env e){
    IV4Router.ExactOutputSingleParams params;
    
    Conversions.Currency currencyOut = params.zeroForOne ? params.poolKey.currency1 : params.poolKey.currency0;
    
    int256 deltaBefore = getCurrencyDeltaExt(currencyOut, currentContract);

    uint256 amountOut;
    if(params.amountOut == 0){
        amountOut = require_uint256(-deltaBefore);
    }else{
        amountOut = params.amountOut;
    }

    require params.poolKey.hooks != currentContract;

    swapExactOutSingle(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyOut, currentContract);

    assert require_int256(deltaAfter - deltaBefore) <= amountOut && require_int256(deltaAfter - deltaBefore) >= 0; 
}

// passed
rule swapExactOutSingleValidateAmountIn(env e){
    IV4Router.ExactOutputSingleParams params;
    
    Conversions.Currency currencyIn = params.zeroForOne ? params.poolKey.currency0 : params.poolKey.currency1;

    int256 deltaBefore = getCurrencyDeltaExt(currencyIn, currentContract);

    require params.poolKey.hooks != currentContract;

    swapExactOutSingle(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyIn, currentContract);

    assert require_int256(deltaBefore - deltaAfter) <= params.amountInMaximum; 
}

// passed
rule swapExactOutShouldIncreaseTokenOutBalance(env e){
    IV4Router.ExactOutputParams params;
    
    Conversions.Currency currencyOut = params.currencyOut;
    
    int256 deltaBefore = getCurrencyDeltaExt(currencyOut, currentContract);

    uint256 amountOut;
    if(params.amountOut == 0){
        amountOut = require_uint256(-deltaBefore);
    }else{
        amountOut = params.amountOut;
    }

    require params.path.length == 1 && params.path[0].hooks != currentContract;

    swapExactOut(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyOut, currentContract);

    assert require_int256(deltaAfter - deltaBefore) <= amountOut && require_int256(deltaAfter - deltaBefore) >= 0; 
}

rule swapExactOutValidateAmountIn(env e){
    IV4Router.ExactOutputParams params;

    uint256 lastIndex = require_uint256(params.path.length - 1);

    Conversions.Currency currencyIn = params.path[0].intermediateCurrency;

    int256 deltaBefore = getCurrencyDeltaExt(currencyIn, currentContract);
    
    require params.path[0].hooks != currentContract;

    swapExactOut(e, params);

    int256 deltaAfter = getCurrencyDeltaExt(currencyIn, currentContract);

    assert currencyIn != params.path[lastIndex].intermediateCurrency => require_int256(deltaBefore - deltaAfter) <= params.amountInMaximum;  
}

rule swapExactOutShouldCallAllPools(env e){

    IV4Router.ExactOutputParams params;

    require calls == 0;

    uint256 length = require_uint256(params.path.length);

    require length > 1;

    swapExactOut(e, params);

    assert calls == length; 
}

// passed
rule validateSettleTakePair(env e){
    Conversions.Currency currencyIn;
    Conversions.Currency currencyOut;

    require currentContract != poolManager() && msgSender() != poolManager();

    int256 deltaBeforeIn = getCurrencyDeltaExt(currencyIn, currentContract);
    int256 deltaBeforeOut = getCurrencyDeltaExt(currencyOut, currentContract);

    settleTakePair(e, currencyIn, currencyOut);

    int256 deltaAfterIn = getCurrencyDeltaExt(currencyIn, currentContract);
    int256 deltaAfterOut = getCurrencyDeltaExt(currencyOut, currentContract);

    assert deltaAfterIn == 0;
    assert deltaAfterOut == 0;
}

// passed
rule validateSettleAll(env e){
    Conversions.Currency currency;
    uint256 maxAmount;

    int256 debt = getCurrencyDeltaExt(currency, currentContract);

    require msgSender() != poolManager();

    settleAll(e, currency, maxAmount);

    assert getCurrencyDeltaExt(currency, currentContract) == 0;
}

// passed
rule validateSettleAllRevert(env e){
    Conversions.Currency currency;
    uint256 maxAmount;

    int256 debt = getCurrencyDeltaExt(currency, currentContract);

    require msgSender() != poolManager();

    settleAll@withrevert(e, currency, maxAmount);

    bool revertResult = lastReverted;
    assert require_uint256(-debt) > maxAmount => revertResult; 
}

// passed
rule validateTakeAll(env e){
    Conversions.Currency currency;
    uint256 minAmount;

    int256 credit = getCurrencyDeltaExt(currency, currentContract);

    address recipient = msgSender();

    uint256 balanceBefore = balanceOfCVL(Conv.fromCurrency(currency), recipient);

    require recipient != poolManager();

    takeAll@withrevert(e, currency, minAmount);

    bool revertResult = lastReverted;

    assert credit < minAmount => revertResult;

    assert revertResult ? getCurrencyDeltaExt(currency, currentContract) == credit : getCurrencyDeltaExt(currency, currentContract) == 0; 

    assert !revertResult => balanceOfCVL(Conv.fromCurrency(currency), recipient) == balanceBefore + credit; 
}

rule validateTakePortion(env e){
    Conversions.Currency currency;
    address recipient;
    uint256 bips;

    int256 credit = getCurrencyDeltaExt(currency, currentContract);
    address actualRecipient = getRecipient(recipient, msgSender());
    uint256 balanceBefore = balanceOfCVL(Conv.fromCurrency(currency), actualRecipient);


    require actualRecipient != poolManager();

    takePortion(e, currency, recipient, bips);

    assert getCurrencyDeltaExt(currency, currentContract) == credit - credit*bips/10000;

    uint256 balanceAfter = balanceOfCVL(Conv.fromCurrency(currency), actualRecipient);

    assert  balanceAfter == require_uint256(balanceBefore + credit*bips/10000); 
}

function getRecipient(address recipient, address sender) returns address{

    if(recipient == 1){
        return sender;
    }else if(recipient == 2){
        return currentContract;
    }else{
        return recipient;
    }

}