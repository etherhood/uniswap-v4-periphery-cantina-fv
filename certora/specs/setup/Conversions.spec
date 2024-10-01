using Conversions as Conv;

methods {
    function Conv.fromCurrency(Conversions.Currency) external returns (address) envfree;
    function Conv.toCurrency(address) external returns (Conversions.Currency) envfree;
    function Conv.poolKeyToId(Conversions.PoolKey) external returns (bytes32) envfree;
    function Conv.positionKey(address,int24,int24,bytes32) external returns (bytes32) envfree;
    function Conv.amount0(Conversions.BalanceDelta) external returns (int128) envfree;
    function Conv.amount1(Conversions.BalanceDelta) external returns (int128) envfree;
    function Conv.hashConfigElements(Conversions.Currency,Conversions.Currency,uint24,int24,address,int24,int24) external returns (bytes32) envfree;    
    function Conv.wrapToPoolId(bytes32) external returns (Conversions.PoolId) envfree;
    function Conv.positionInfoToBytes32(Conversions.PositionInfo) external returns (bytes32) envfree;
    function Conv.getPositionInfo(Conversions.PoolKey,int24,int24) external returns (Conversions.PositionInfo) envfree;
    function Conv.hasSubscriber(Conversions.PositionInfo) external returns (bool) envfree;
    function Conv.getPoolId(Conversions.Currency,Conversions.Currency,int24,uint24,address) external returns (bytes32) envfree;
}

function PoolKeyToId(Conversions.PoolKey key) returns bytes32 {
    return Conv.poolKeyToId(key);
}

function getPositionKey(address owner, int24 tickLower, int24 tickUpper, bytes32 salt) returns bytes32 {
    return Conv.positionKey(owner, tickLower, tickUpper, salt);
}

function getPositionInfo(Conversions.PoolKey key, int24 tickLower, int24 tickUpper) returns Conversions.PositionInfo {
    return Conv.getPositionInfo(key, tickLower, tickUpper);
}

function positionInfoToBytes32(Conversions.PositionInfo info) returns bytes32 {
    return Conv.positionInfoToBytes32(info);
}