from data import DataHandler
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from event import OrderEvent
import queue
import math

"""
    Ordering issue

    event que

    add 3 sell events
    add 3 buy wait for fill empty

    portfolio
    recieves 3 sell
    sends 3 order
    recieves 3 fills

    so portfolio needs intrernal waiting for fill que when it sends orders
    and buy signals need to be able to say wait till fill que is empty to place order
    to implement wait till fill and a 3rd que to save signals until fills have been completed

"""


class Portfolio:
    """
        Data
        holdings: array of dict that store date and cash
            [
                {"datetime": start_date, "cash":starting cash, "stock_value":0},
                {"datetime": timestamp, "cash":current cash on hand, "stock_vale": current stock value},
                ...
                {"datetime": end_date, "cash":final cash}
            ]
        current_holdings: dict of current holdings no datetime 
                            a single entry to holdings
            {
                "cash":
                "stock_value":
                "total":
            }
        positions: array of dict that store date and stock held
            [
                {"datetime": start_date, "position":0},
                {"datetime": timestamp, "position":current position held},
                ...
                {"datetime": end_date, "positon":final value of position}
            ]
        current_positions: dict of stock position
            {
                "stock": amount of stock int
            }
    """

    def __init__(self, dataHandler, events, starting_capital=100000):

        """
            Params:
                dataHandler:
                    Type: 
                        DataHandler()
                    Description:
                        holds historic data for timeseries
                events:
                    Type:
                        Queue() of Event()
                    Description:
                        the main event que, used to add generated events
                starting_capital:
                    Type:
                        Int
                    Description:
                        the starting capital of the portfolio           
        """
        self.events = events
        self.dataHandler = dataHandler
        self.symbol_list = dataHandler.symbol_list
        self.starting_capital = starting_capital
        # Holdings init
        self.holdings = self.construct_holdings()

        self.current_holdings = self.construct_current_holdings()

        # positions init
        self.positions = self.construct_positions()

        self.current_positions = self.construct_current_positions()

        # balance_ratio if needed
        self.balance_ratio = None

    def construct_positions(self):
        """
            returns:
                Type:
                    
                Description:
                    list of dictionary of stock : number of stock which is 0
                Example:
                    [
                        {
                            "datetime" : datetime()
                            "stock1"   : int
                            ...
                            "stocklast": int
                        }
                    ]
        """
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d["datetime"] = self.dataHandler.start_date
        return [d]

    def construct_holdings(self):
        """
            returns:
                Type:
                    [{string: int, string:datetime}]
                Description:
                    list of dictionary of stock : number of stock which is 0
                Example:
                    [
                        {
                            "datetime" : datetime()
                            "cash"     : int
                            "total"    : int
                            "stock1"   : int
                            ...
                            "stocklast": int
                        }
                    ]
        """
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d["datetime"] = self.dataHandler.start_date
        d["cash"] = self.starting_capital
        d["total"] = self.starting_capital
        return [d]

    def construct_current_positions(self):
        """
            returns:
            Type:
                dict {}
            Description:
                dictionary of stock : number of stock which is 0
            Example:
                    {
                        "datetime": datetime()
                        "stock1": int,
                        ... 
                        "stocklast": int,
                    }
        """
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d["datetime"] = self.dataHandler.start_date
        return d

    def construct_current_holdings(self):
        """
            returns:
                Type:
                    dict {string: int, string:datetime}
                Description:
                    list of dictionary of stock : number of stock which is 0
                Example:
                        {
                            "datetime" : datetime()
                            "cash"     : int
                            "total"    : int
                            "stock1"   : int
                            ...
                            "stocklast": int
                        }
        """
        d = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
        d["datetime"] = self.dataHandler.start_date
        d["cash"] = self.starting_capital
        d["total"] = self.starting_capital
        return d

    def update(self):
        """
            updates (adds new entry in form of dict) to holdings and positions using the latest data from dataHandler

        """
        timestamp = self.dataHandler.get_latest_bar(self.symbol_list[0])[0]

        # avoids duplicating the first entry
        if timestamp != self.dataHandler.start_date:

            # update positions
            temp_positions = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
            temp_positions["datetime"] = timestamp

            for s in self.symbol_list:
                temp_positions[s] = self.current_positions[s]

            self.positions.append(temp_positions)

            # update holdings
            temp_holdings = dict((k, v) for k, v in [(s, 0) for s in self.symbol_list])
            temp_holdings.update(
                {
                    "datetime": timestamp,
                    "cash": self.current_holdings["cash"],
                    "total": self.current_holdings["cash"],
                }
            )

            for s in self.symbol_list:
                temp_holdings[s] = self.current_positions[
                    s
                ] * self.dataHandler.get_latest_bar_value(s, "adj_close")
                temp_holdings["total"] += temp_holdings[s]

            self.current_holdings["total"] = temp_holdings["total"]

            self.holdings.append(temp_holdings)

    def handle_signal(self, event):

        if event.signal_type == "BUY":
            desired_cash_value = (
                self.balance_ratio[event.symbol] * self.current_holdings[-1]["total"]
            )
            quantity = math.floor(
                desired_cash_value
                / self.dataHandler.get_latest_bar_value(event.symbol, "adj_close")
            )
            order = OrderEvent(symbol=event.symbol, quantity=quantity, direction="BUY")
            self.events.put(order)
        elif event.signal_type == "EXIT":
            quantity = self.current_positions[-1][event.symbol]
            order = OrderEvent(symbol=event.symbol, quantity=quantity, direction="SELL")

    def update_positions_from_fill(self, fill_event):
        directions = {"BUY": 1, "SELL": -1}
        fill_direction = directions[fill_event.direction]

        self.current_positions[fill_event.symbol] += (
            fill_direction * fill_event.quantity
        )

    def update_holdings_from_fill(self, fill_event):

        directions = {"BUY": 1, "SELL": -1}
        fill_direction = directions[fill_event.direction]

        fill_cost = self.dataHandler.get_latest_bar_value(
            fill_event.symbol, "adj_close"
        )
        cost = fill_direction * fill_cost * fill_event.quantity

        self.current_holdings[fill_event.symbol] = self.current_positions[
            fill_event.symbol
        ] * self.dataHandler.get_latest_bar_value(fill_event.symbol, "adj_close")
        self.current_holdings["cash"] -= cost

    def process_fill(self, event):
        """
            updates the portfolio based on the fill order that comes from execution
        """
        self.update_positions_from_fill(event)
        self.update_holdings_from_fill(event)

    # Stats section

    def create_equity_curve(self):
        curve = pd.DataFrame(self.holdings)
        curve.set_index("datetime")
        curve["returns"] = curve["total"].pct_change()
        curve["equity_curve"] = (1.0 + curve["returns"]).cumprod()
        self.equity_curve = curve

    def create_sharp_ratio(self, returns, periods=252):
        """
            returns is a pandas series of percentage returns
            periods can be daily 252, hourly 252*6.5, minutely 252*6.5*60
        """
        return np.sqrt(periods) * (np.mean(returns) / np.std(returns))

    def create_drawdowns(self, pnl):
        """
            keeps track of the largest peak-to-trough drawdown of the Pnl curve and duration of drawdone
            Pnl is a pandas series of percentage returns
        """

        hwm = [0]
        drawdown = pd.Series(index=pnl.index)
        duration = pd.Series(index=pnl.index)

        for t in range(1, len(pnl.index)):
            hwm.append(max(hwm[t - 1], pnl[t]))
            drawdown[t] = hwm[t] - pnl[t]
            duration[t] = 0 if drawdown[t] == 0 else duration[t - 1] + 1

        return drawdown, drawdown.max(), duration.max()

    def output_summary_stats(self):

        self.create_equity_curve()

        total_return = self.equity_curve["equity_curve"].iloc[-1]
        returns = self.equity_curve["returns"]
        pnl = self.equity_curve["equity_curve"]

        sharp_ratio = self.create_sharp_ratio(returns)
        drawdown, max_dd, dd_duration = self.create_drawdowns(pnl)
        self.equity_curve["drawdown"] = drawdown

        stats = [
            ("Total Return", "{}%".format(round((total_return - 1.0) * 100, 2))),
            ("Sharp Ratio", "{}".format(round(sharp_ratio, 2))),
            ("Max Drawdown", "{}".format(round(max_dd * 100, 2))),
            ("Drawdown Duration", "{}".format(dd_duration)),
        ]

        self.equity_curve.to_csv("equity.csv")
        return stats

    def display_results(self):
        # devide figure into 3 parts
        fig = plt.figure()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        self.equity_curve.plot(
            kind="line",
            x="datetime",
            y="equity_curve",
            ax=ax1,
            color="blue",
            legend=False,
            grid=True,
        )
        ax1.set_ylabel("Equity")
        ax1.set_xlabel(None)
        ax1.set_yticks(
            np.arange(
                self.equity_curve["equity_curve"].min(),
                self.equity_curve["equity_curve"].max(),
                0.05,
            )
        )
        self.equity_curve.plot(
            kind="line",
            x="datetime",
            y="returns",
            ax=ax2,
            color="black",
            legend=False,
            grid=True,
        )
        ax2.set_ylabel("returns %")
        ax2.set_xlabel(None)
        ax2_y_step = (
            self.equity_curve["returns"].max() - self.equity_curve["returns"].min()
        ) / 3
        ax2.set_yticks(
            np.arange(
                self.equity_curve["returns"].min(),
                self.equity_curve["returns"].max() + ax2_y_step,
                ax2_y_step,
            )
        )
        self.equity_curve.plot(
            kind="line",
            x="datetime",
            y="drawdown",
            ax=ax3,
            color="red",
            legend=False,
            grid=True,
        )
        ax3.set_ylabel("Drawdown %")
        ax3.set_yticks(
            np.arange(
                self.equity_curve["drawdown"].min(),
                self.equity_curve["drawdown"].max(),
                0.05,
            )
        )
        plt.tight_layout()
        plt.show()

