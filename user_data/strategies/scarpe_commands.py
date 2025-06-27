"""
Custom commands for ScarpeStrategy
"""
from freqtrade.rpc.api_server.api_v1 import router
from freqtrade.rpc.api_server.api_schemas import ScarpeStrategyParams, ResultMsg
from fastapi import Depends, HTTPException
from freqtrade.rpc.api_server.deps import get_rpc
from freqtrade.rpc import RPC

@router.post("/custom/scarpe/set_params", response_model=ResultMsg, tags=["custom"])
def set_scarpe_params(payload: ScarpeStrategyParams, rpc: RPC = Depends(get_rpc)):
    """Set ScarpeStrategy parameters via custom command"""
    try:
        # Cập nhật parameters
        strategy = rpc._freqtrade.strategy
        if strategy and hasattr(strategy, 'OC'):
            strategy.OC.value = payload.OC
            strategy.Extent.value = payload.Extent
            strategy.Amount.value = payload.Amount
            strategy.TakeProfit.value = payload.TakeProfit
            strategy.Reduce.value = payload.Reduce
            strategy.UpReduce.value = payload.UpReduce
            
            return {"status": f"ScarpeStrategy parameters updated: OC={payload.OC}, Extent={payload.Extent}, Amount={payload.Amount}, TP={payload.TakeProfit}, Reduce={payload.Reduce}, UpReduce={payload.UpReduce}"}
        else:
            raise HTTPException(status_code=400, detail="ScarpeStrategy not loaded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating parameters: {str(e)}")

@router.get("/custom/scarpe/get_params", response_model=ScarpeStrategyParams, tags=["custom"])
def get_scarpe_params(rpc: RPC = Depends(get_rpc)):
    """Get current ScarpeStrategy parameters"""
    try:
        strategy = rpc._freqtrade.strategy
        if strategy and hasattr(strategy, 'OC'):
            return ScarpeStrategyParams(
                OC=strategy.OC.value,
                Extent=strategy.Extent.value,
                Amount=strategy.Amount.value,
                TakeProfit=strategy.TakeProfit.value,
                Reduce=strategy.Reduce.value,
                UpReduce=strategy.UpReduce.value
            )
        else:
            raise HTTPException(status_code=400, detail="ScarpeStrategy not loaded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting parameters: {str(e)}") 