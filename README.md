# Introduction 
This code downloads historical data (1 minute candles) and backtest an easy strategy based on two ewma crossing.

# Getting Started
1.	Installation process
Use virtual environment with python 3.8+.
If you need help with virtual env here is a great explenation https://realpython.com/python-virtual-environments-a-primer/.
2.	Software dependencies
Install dependencies by running `pip install -r requirements.txt`
3.	Running backtesting
``` python
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
```
