import queue
from my_utils import params_to_attr


class Backtest:
    """
        Connects all the classes of the trading system and runs the backtest
        ouputing stats and results.
    """

    @params_to_attr
    def __init__(
        self,
        csv_dir,
        symbol_list,
        inital_capital,
        start_date,
        end_date,
        data_handler_cls,
        execution_handler_cls,
        portfolio_cls,
        stratergy_cls,
    ):
        """
        Params:
            csv_dir: 
                Type: 
                    String
                Description: 
                    directory path where csv files are located
                Example: 
                    "E:\\Code\\EventDrivenTrading\\stock_dfs"
            
            symbol_list: 
                Type: 
                    Array []
                Description: 
                    list of ticker/symbol names of the csv files required from the folder
                Example: 
                    ["APPL", "GOOG"]
                    the csv files are assumed to be of form "symbol.csv"
            
            initial_capital:
                Type:
                    Int
                Description:
                    Starting capital for portfolio
                Example:
                    100,000
            
            start_date:
                Type:
                    DateTime
                Description:
                    Starting date for the back test (Stock data will be gathered from this date till end date)
                Example
                    Datetime.datetime(2012, 1, 1) #(year, month, day)
            
            end_date:
                same as starting date above but the end date
            
            data_handler_cls:
                Type:
                    DataHandler()
                Description:
                    class that collects desired data, formats it, triggers market events and serves up desired bars
            
            execution_handler_cls:
                Type:
                    ExecutionHandler()
                Description:
                    responsible for the modelling of brokerages and exchanges, used to handle orders
            
            portfolio_cls:
                Type:
                    Portfolio()
                Description:
                    responsible for the holdings and cash data, handling fills, outputing summary stats
            
            stratergy_cls:
                Type:
                    Stratergy()
                Description:
                    looks at market data and generates trading signals    
        """

        self.events = queue.Queue()
        self.events_priority_2 = queue.Queue()

        self.signals = 0
        self.orders = 0
        self.fills = 0
        self.num_strats = 1

        self._generate_trading_instances()

    def _generate_trading_instances(self):
        print("Creating DataHandler, Stratergy, Portfolio")
        self.data_handler = self.data_handler_cls(
            self.events, self.csv_dir, self.symbol_list, self.start_date, self.end_date
        )
        self.portfolio = self.portfolio_cls(self.data_handler, self.events)
        self.stratergys = [self.stratergy_cls(self.data_handler, self.events)]
        self.execution_handler = self.execution_handler_cls(self.events)

    def _run_backtest(self):

        """
            Runs the data generater and main event loop
        """

        count = 0
        while True:
            count += 1
            # Get market event/data
            if self.data_handler.finished == False:
                self.data_handler.update_bars()
            else:
                break

            self.handle_events()
            self.handle_events_priority_2
            self.handle_events()

    def handle_events(self):
        # handle events in que
        while True:

            # get event from queue
            try:
                event = self.events.get(False)
            except queue.Empty:
                break
            else:

                if event is not None:
                    # switch on event type
                    if event.type == "MARKET":
                        # Handle processing of new market data
                        for s in self.stratergys:
                            s.calculate_signal()
                        self.portfolio.update()
                    elif event.type == "SIGNAL":
                        self.signals += 1
                        self.portfolio.handle_signal(event)

                    elif event.type == "ORDER":
                        self.orders += 1
                        self.execution_handler.execute_order(event)
                    # print("signal : ", signal)
                    elif event.type == "FILL":
                        self.fills += 1
                        self.portfolio.process_fill(event)

    def handle_events_priority_2(self):
        # handle events in priority 2 que
        while True:

            # get event from queue
            try:
                event = self.events_priority_2.get(False)
            except queue.Empty:
                break
            else:

                if event is not None:
                    if event.type == "SIGNAL":
                        self.signals += 1
                        self.portfolio.handle_signal(event)

                    elif event.type == "ORDER":
                        self.orders += 1
                        self.execution_handler.execute_order(event)
                    # print("signal : ", signal)
                    elif event.type == "FILL":
                        self.fills += 1
                        self.portfolio.process_fill(event)

    def _output_performance(self):
        print("Signals : {}".format(self.signals))
        print("Orders : {}".format(self.orders))
        print("Fills : {}".format(self.fills))

        stats = self.portfolio.output_summary_stats()
        print(stats)
        self.portfolio.display_results()

    def simulate_trading(self):
        """
            Entry point for running the backtest
        """
        self._run_backtest()
        self._output_performance()
