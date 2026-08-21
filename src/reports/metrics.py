from dataclasses import dataclass

from ..backtest.engine import BacktestResult
from ..backtest.engine import EquityPoint

@dataclass(frozen=True)
class Metrics:
    total_pnl: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    average_pnl: float
    

def calculate_max_drawdown(equity_curve: list[EquityPoint]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0].equity
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity)
        drawdown = (peak - point.equity) / peak
        max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown


def calculate_annualized_return(result: BacktestResult) -> float:
    if len(result.equity_curve) < 2:
        return 0.0

    start = result.equity_curve[0].timestamp
    end = result.equity_curve[-1].timestamp
    total_days = (end - start).total_seconds() / 86400
    if total_days <= 0:
        return 0.0

    return (result.final_cash / result.initial_cash) ** (365.25 / total_days) - 1


def calculate_metrics(result: BacktestResult) -> Metrics:
    total_pnl = result.final_cash - result.initial_cash
    total_return = total_pnl / result.initial_cash
    annualized_return = calculate_annualized_return(result)
    max_drawdown = calculate_max_drawdown(result.equity_curve)
    trade_count = len(result.trades)
    win_rate = sum(1 for trade in result.trades if trade.net_pnl is not None and trade.net_pnl > 0) / trade_count if trade_count > 0 else 0.0
    average_pnl = sum(trade.net_pnl for trade in result.trades if trade.net_pnl is not None) / trade_count if trade_count > 0 else 0.0
    
    return Metrics(
        total_pnl=total_pnl,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        trade_count=trade_count,
        win_rate=win_rate,
        average_pnl=average_pnl
    )
    
