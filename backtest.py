import time
import matplotlib.pyplot as plt
import pandas as pd
import download_data

from pytz import timezone


class Simulation(object):

    def __init__(self, market, print_from=None, print_to=None, fee=0.0006, interval_s=4320, interval_f=240, leverage=1):
        self.market = market
        self.print_from = print_from
        self.print_to = print_to
        self.fee = fee
        self.profit = 0.0
        self.count = 0
        self.b_markers_on = []
        self.b_markers_value = []
        self.s_markers_on = []
        self.s_markers_value = []
        self.e_markers_on = []
        self.e_markers_value = []
        self.cum_rel_profit = 0
        self.max_change = 0
        self.min_change = 0
        self.plot_distance = 0.1
        self.hodl_profit = 0
        self.interval_s = interval_s
        self.leverage = leverage
        self.interval_f = interval_f
        self.portfolio = self.beg_portfolio = 1000
        self.display_value = []
        self.display_hodl = []
        self.display_value_on = []
        self.position_amount = 0

    def prepare_ftx_api_data(self,):
        start = time.time()

        df = pd.read_csv(f'data/ftx_{self.market.upper()}.csv')
        df.set_index(pd.to_datetime(df['startTime'], format='%Y-%m-%dT%H:%M:%S'), inplace=True)

        df['timestamp'] = df['time']

        print(f'Load data took {time.time() - start}')

        return df

    def data(self):
        start = time.time()

        df = self.prepare_ftx_api_data()
        df['timestamp'] = df.index.to_series()

        df['mean_s'] = df['close'].ewm(span=self.interval_s).mean()
        df['mean_f'] = df['close'].ewm(span=self.interval_f).mean()

        simulation_points = df.loc[self.print_from:self.print_to].to_dict('records')

        print(f'EWMA cross data prep for {self.market} took {time.time() - start}')

        self.df = df
        self.simulation_points = simulation_points

    def _print_change(self, msg, item, change, rel_profit):
        print('{:<10}  {:<30}  {:<15.6f}  {:=+12.4f}  {:=+10.2f} {:=+10.2f} %'.format(msg, str(item['timestamp'].astimezone(timezone('Europe/Prague'))), item['close'], self.portfolio, change, rel_profit * 100))

    def _calc_change(self, prev_profit, value, position):
        change = self.profit - prev_profit
        self.portfolio = self.portfolio + change
        if position == 'short':
            rel_profit = - change / (self.position_amount * value)
        else:
            rel_profit = change / (self.position_amount * value)
        self.cum_rel_profit += rel_profit
        if change > self.max_change:
            self.max_change = change
        elif change < self.min_change:
            self.min_change = change
        self.count += 1
        return change, rel_profit

    def _get_amount(self, price):
        return self.portfolio * self.leverage / price

    def _enter_buy_position(self, value, item, msg, fee):
        prev_profit = self.profit
        self.position_amount = self._get_amount(item['close'])
        self.profit = self.profit - self.position_amount * item['close'] * fee
        change, rel_profit = self._calc_change(prev_profit, value, position='long')
        self._print_change(msg, item, change, rel_profit)
        self.b_markers_on.append(item['timestamp'])
        self.b_markers_value.append(float(item['close']) - self.plot_distance)

    def _enter_sell_position(self, value, item, msg, fee):
        prev_profit = self.profit
        self.position_amount = self._get_amount(item['close'])
        self.profit = self.profit - self.position_amount * item['close'] * fee
        change, rel_profit = self._calc_change(prev_profit, value, position='short')
        self._print_change(msg, item, change, rel_profit)
        self.s_markers_on.append(item['timestamp'])
        self.s_markers_value.append(float(item['close']) + self.plot_distance)

    def _exit_partial_position(self, position, item, value, msg, fee, fraction):
        if value:
            prev_profit = self.profit
            self.position_amount = self.position_amount * fraction
            if position == 'short' and value < 0:
                self.profit = self.profit - self.position_amount * (item['close'] * (1 + fee) + value)
                change, rel_profit = self._calc_change(prev_profit, value, position)
            if position == 'long' and value > 0:
                self.profit = self.profit + self.position_amount * (item['close'] * (1 - fee) - value)
                change, rel_profit = self._calc_change(prev_profit, value, position)
            self.position_amount = self.position_amount / fraction * (1 - fraction)
            self._print_change(msg, item, change, rel_profit)
            self.e_markers_on.append(item['timestamp'])
            self.e_markers_value.append(float(item['close']))

    def simulate(self, value=0, status=None, exit_price=0, close_loss=0):
        for item in self.simulation_points:
            if status in ['bought', 'bought_1'] and item['mean_f'] < item['mean_s']:
                self._exit_partial_position(position='long', item=item, value=value, msg='sbexit', fee=self.fee, fraction=1)
                status = None
                if value > 0:
                    close_loss = item['close'] / value
                value = 0
            if status in ['sold', 'sold_1'] and item['mean_f'] > item['mean_s']:
                if status == 'sold':
                    self._exit_partial_position(position='short', item=item, value=value, msg='ssexit', fee=self.fee, fraction=1)
                status = None
                value = 0
            if status == 'sold' and item['close'] <= exit_price:
                self._exit_partial_position(position='short', item=item, value=value, msg='ssexit_1', fee=0, fraction=1)
                status = 'sold_1'
            if status is None and item['mean_s'] < item['mean_f']:
                value = item['close']
                self._enter_buy_position(value=value, item=item, msg='buy', fee=self.fee)
                status = 'bought'
            if status is None and item['mean_s'] > item['mean_f']:
                value = - item['close']
                self._enter_sell_position(value=value, item=item, msg='sell', fee=self.fee)
                status = 'sold'
                if close_loss < 1 and close_loss > 0:
                    exit_price = item['close'] * ((close_loss - 1) * 1 + 1)
                else:
                    exit_price = item['close'] * 0.995

            if status in ['bought', 'bought_1']:
                self.display_value.append(self.portfolio + self.position_amount * (item['close'] - value))
            elif status in ['sold', 'sold_1']:
                self.display_value.append(self.portfolio - self.position_amount * (item['close'] + value))
            else:
                self.display_value.append(self.portfolio)
            self.display_hodl.append((1 + (self.leverage * (item['close'] / self.simulation_points[0]['close'] - 1))) * self.beg_portfolio)
            self.display_value_on.append(item['timestamp'])

            if self.portfolio <= 0:
                break

        self.cum_rel_profit = round(self.profit / self.beg_portfolio * 100, 2)
        self.hodl_profit = (self.simulation_points[-1]['close'] / self.simulation_points[0]['close'] - 1)

        print(f'Number of trades {self.count}.')
        print(f'Absolute profit {self.profit}.')
        print(f'Relative profit {self.cum_rel_profit} %.')
        print(f'Relative hodl profit {round(self.hodl_profit * 100, 2)} %.')
        print(f'Average relative profit {round(self.cum_rel_profit / self.count if self.count else 0, 2)} %.')

    def plot_strategy(self):

        df = self.df.loc[self.print_from:self.print_to]

        fig, (ax1, ax2) = plt.subplots(2, sharex=True)

        ax1.plot(df.index, df['close'], label='close')
        ax1.plot(pd.to_datetime(self.b_markers_on), self.b_markers_value, 'g^', label='buy mark')
        ax1.plot(pd.to_datetime(self.s_markers_on), self.s_markers_value, 'rv', label='sell mark')
        ax1.plot(pd.to_datetime(self.e_markers_on), self.e_markers_value, 'x', label='exit')
        ax1.plot(df.index, df['mean_f'], label='mean_f', color='k')
        ax1.plot(df.index, df['mean_s'], label='mean_s', color='r')
        ax1.set_title('Price and Indicators')
        ax1.legend()

        ax2.plot(pd.to_datetime(self.display_value_on), self.display_value, label='strategy', color='r')
        ax2.plot(pd.to_datetime(self.display_value_on), self.display_hodl, label='hodl', color='k')
        ax2.axhline(y=0)
        ax2.axhline(y=self.beg_portfolio)
        ax2.set_title('Portfolio Value')
        ax2.legend()

        fig.suptitle('Backtesting', fontsize=16)
        plt.legend()
        plt.show()


if __name__ == "__main__":
    # Choose your market (works best with perpetual futures - ending "-PERP")
    market = 'BTC-PERP'
    # Data will be downloaded from 2019-08-01 00:00:00+00:00 by default
    download_data.main(market=market)
    '''
    You can set the following parameters when creating a Simulation instance
    
    market (str): the selected market (e.g., 'ETH-PERP')
    print_from (str): you can choose a date from '2019-08-01 00:00:00+00:00'
    print_to (str): you can limit the end of the range (same date format as print_from)
    fee (float): set in decimal number (e.g., 0.07% = 0.0007)
    interval_s (int): slow ewma in minutes (e.g., 120 = 2 hours)
    interval_f (int): fast ewma in minutes (e.g., 120 = 2 hours)
    leverage (int): if leverage <= 1 there is no leverage
    '''
    sim = Simulation(market=market, print_from='2019-08-01 00:00:00+01:00', fee=0.0006, interval_s=4320, interval_f=240, leverage=1)
    # Prepare data
    sim.data()
    # Run simul. iteration
    sim.simulate()
    # Plot the results
    sim.plot_strategy()
