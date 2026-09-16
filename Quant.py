if __package__:
    from .src.backtest.backtest import demo as run_backtest_demo, run_backtest
    from .src.backtest.config import BacktestConfig
    from .src.strategies.sma_cross import SmaCrossConfig
    from .src.strategies.donchian import DonchianConfig
    from .src.strategies.momentum import MomentumConfig
    from .src.strategies.mean_reversion import MeanReversionConfig
    from .src.data.data_loader import CsvDataLoader
    from pathlib import Path
else:
    from src.backtest.backtest import demo as run_backtest_demo, run_backtest
    from src.backtest.config import BacktestConfig
    from src.strategies.sma_cross import SmaCrossConfig
    from src.strategies.donchian import DonchianConfig
    from src.strategies.momentum import MomentumConfig
    from src.strategies.mean_reversion import MeanReversionConfig
    from src.data.data_loader import CsvDataLoader
    from pathlib import Path


def prompt_sma_config() -> SmaCrossConfig:
    while True:
        try:
            fast = int(input("请输入快速均线窗口大小（默认值为 25）:") or 25)
            slow = int(input("请输入慢速均线窗口大小（默认值为 99）:") or 99)
            target = float(input("请输入目标仓位大小（0 到 1.0 之间的小数，默认值为 0.2）:") or 0.2)
            return SmaCrossConfig(fast_window=fast, slow_window=slow, target_size=target)
        except ValueError as e:
            print(f"参数无效: {e}，请重新输入")


def prompt_donchian_config() -> DonchianConfig:
    while True:
        try:
            window = int(input("请输入窗口大小（默认值为20）:") or 20)
            target = float(input("请输入目标仓位大小（0 到 1.0 之间的小数，默认值为 0.2）:") or 0.2)
            return DonchianConfig(window=window, target_size=target)
        except ValueError as e:
            print(f"参数无效: {e}，请重新输入")


def prompt_momentum_config() -> MomentumConfig:
    while True:
        try:
            lookback = int(input("请输入动量窗口大小（默认值为 20）:") or 20)
            threshold = float(input("请输入触发阈值（0 到 1 之间的小数，默认值为 0.0）:") or 0.0)
            target = float(input("请输入目标仓位大小（0 到 1.0 之间的小数，默认值为 0.2）:") or 0.2)
            return MomentumConfig(lookback=lookback, threshold=threshold, target_size=target)
        except ValueError as e:
            print(f"参数无效: {e}，请重新输入")


def prompt_mean_reversion_config() -> MeanReversionConfig:
    while True:
        try:
            window = int(input("请输入均值窗口大小（默认值为 20）:") or 20)
            entry_z = float(input("请输入入场阈值 entry_z（默认值为 2.0）:") or 2.0)
            exit_z = float(input("请输入平仓阈值 exit_z（默认值为 0.5）:") or 0.5)
            target = float(input("请输入目标仓位大小（0 到 1.0 之间的小数，默认值为 0.2）:") or 0.2)
            return MeanReversionConfig(window=window, entry_z=entry_z, exit_z=exit_z, target_size=target)
        except ValueError as e:
            print(f"参数无效: {e}，请重新输入")


def main() -> None:
    print("请选择运行方式：")
    print("1. 本地回测演示（Sma交叉策略）")
    print("2. 本地回测演示（DonChian Channel策略）")
    print("3. 本地回测演示（满仓买入并持有策略）")
    print("4. 本地回测演示（动量趋势跟踪策略）")
    print("5. 本地回测演示（均值回归策略）")
    choice = input("输入数字:").strip()
    if choice == "1":
        config = prompt_sma_config()
        run_backtest_demo(
            strategy_name="SMA_Cross",
            strategy_config=config,
        )
    elif choice == "2":
        config = prompt_donchian_config()
        run_backtest_demo(
            strategy_name="Donchian_Channel",
            strategy_config=config,
        )
    elif choice == "3":
        run_backtest_demo(strategy_name="Buy_and_Hold")
    elif choice == "4":
        config = prompt_momentum_config()
        run_backtest_demo(
            strategy_name="Momentum",
            strategy_config=config,
        )
    elif choice == "5":
        config = prompt_mean_reversion_config()
        run_backtest_demo(
            strategy_name="Mean_Reversion",
            strategy_config=config,
        )
    else:
        print("请输入数字:")


if __name__ == "__main__":
    main()
