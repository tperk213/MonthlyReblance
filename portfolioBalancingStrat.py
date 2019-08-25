from data import DataHandler
from portfolio import Portfolio
from event import SignalEvent
from backtest import Backtest
from execution import ExecutionHandler
from my_utils import params_to_attr
from stratergy import Stratergy

import numpy
import pandas as pd
import pandas_datareader.data as web
import os
from datetime import datetime
import statsmodels.api as sm
import queue
import calendar

# get data from yahoo finance
def save_data_from_web():

    raw_data = {
        "SPY": web.DataReader(
            "SPY", "yahoo", datetime(2003, 9, 29), datetime(2016, 10, 12)
        ),
        "AGG": web.DataReader(
            "AGG", "yahoo", datetime(2003, 9, 29), datetime(2016, 10, 12)
        ),
        "IJS": web.DataReader(
            "IJS", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
        "EFA": web.DataReader(
            "EFA", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
        "EEM": web.DataReader(
            "EEM", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
        "JNK": web.DataReader(
            "JNK", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
        "DJP": web.DataReader(
            "DJP", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
        "RWR": web.DataReader(
            "RWR", "yahoo", datetime(2007, 12, 4), datetime(2016, 10, 12)
        ),
    }
    # save data to folder
    out_dir = "E:\\Code\\BackTestingPlatform\\stratergyResearch\\data"

    for key, df in raw_data.items():
        df.to_csv(os.path.join(out_dir, "{}.csv".format(key)))


class end_of_month_rebalance_stratergy(Stratergy):
    def __init__(self, symbol_list, data, events, events_priotity_2):
        """
            Params:
                symbol: list of string symbols that are of interest
                    ["AAPL", "BRW", ]
                data: dataHandler of market data
                    dataHandler object
                events: event queue
                    Queue object of Event()

        """
        self.symbol_list = symbol_list
        self.data = data
        self.events = events
        self.events_priotity_2 = events_priotity_2
        self.previous_date = data.start_date
        self.tickers_invested = self._create_invested_list(symbol_list)

    def _start_of_month(self, date):
        """
            because the end of the month may fall on a weekend or non trading day
            the stratergy checks to see if the date.day is smaller then the last trading day and rebalances then
        """
        return self.previous_date > date.day

    def _create_invested_list(self, symbol_list):
        tickers_invested = {ticker: False for ticker in symbol_list}
        return tickers_invested

    def calculate_signal(self):
        """
            if its the start of the month sell everything and rebuy everything
        """
        bar_date = self.data.get_latest_bar_datetime(self.symbol_list[0])
        if self._start_of_month(bar_date):
            for symbol in self.tickers_invested:
                signal = SignalEvent(symbol, bar_date, "EXIT", 1)
                self.events.put(signal)
            for symbol in self.symbol_list:
                """
                    Check to see if the adj_close isn't nan
                """
                if not numpy.isnan(self.data.get_bar_value(symbol, "adj_close")):
                    signal = SignalEvent(symbol, bar_date, "BUY", 1)
                    self.events_priotity_2.put(signal)


if __name__ == "__main__":

    csv_dir = "E:\\Code\\BackTestingPlatform\\stratergyResearch\\data"
    symbol_list = ["SPY", "IJS", "EFA", "EEM", "AGG", "JNK", "DJP", "RWR"]
    initial_capital = 100000
    # start_date = datetime(2013, 1, 1)
    # end_date = datetime(2014, 1, 1)"

    # Data handler testing
    # events = queue.Queue()
    # data_handler = DataHandler(events, csv_dir, symbol_list)

    backtest = Backtest(
        csv_dir,
        symbol_list,
        initial_capital,
        DataHandler,
        ExecutionHandler,
        Portfolio,
        OLSMRStratergy,
    )

    backtest.simulate_trading()

