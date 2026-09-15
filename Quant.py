if __package__:
    from .src.backtest.backtest import demo as run_backtest_demo
    from .src.strategies.sma_cross import SmaCrossConfig
    from .src.strategies.donchian import DonchianConfig
else:
    from src.backtest.backtest import demo as run_backtest_demo
    from src.strategies.sma_cross import SmaCrossConfig
    from src.strategies.donchian import DonchianConfig


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


def main() -> None:
    print("请选择运行方式：")
    print("1. 本地回测演示（Sma交叉策略）")
    print("2. 本地回测演示（DonChian Channel策略）")
    print("3. 本地回测演示（满仓买入并持有策略）")
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
    else:
        print("请输入数字:")


if __name__ == "__main__":
    main()

