if __package__:
    from .src.backtest.backtest import demo as run_backtest_demo
else:
    from src.backtest.backtest import demo as run_backtest_demo


def main() -> None:
    print("请选择运行方式：")
    print("1. 本地回测演示（Sma交叉策略）")
    print("2. 本地回测演示（买入并持有策略）")
    choice = input("输入 1 或 2:").strip()
    if choice == "1":
        check = False
        while not check:
            fast_window = int(input("请输入快速均线窗口大小（默认值为 10）:") or 10)
            slow_window = int(input("请输入慢速均线窗口大小（默认值为 30）:") or 30)
            if fast_window <= 0 or slow_window <= 0:
                raise ValueError("窗口大小必须为正整数")
            elif fast_window >= slow_window:
                print("快速均线窗口大小必须小于慢速均线窗口大小，请重新输入。")
            else:
                check = True
        run_backtest_demo(strategy_name="sma_cross", param=(fast_window, slow_window))
    elif choice == "2":
        run_backtest_demo(strategy_name="buy_and_hold")
    else:
        print("请输入 1 或 2:")


if __name__ == "__main__":
    main()
 
