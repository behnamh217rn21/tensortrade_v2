# Copyright 2019 The TensorTrade Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License
import ccxt
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from time import sleep

from typing import List, Union
from ccxt import BadRequest

from tensortrade.oms.exchanges import Exchange
from tensortrade.oms.instruments import TradingPair, BTC, USDT, DOGE


class CCXTExchange():
    """An exchange for trading on CCXT-supported cryptocurrency exchanges."""
    def __init__(self, 
                 exchange: Union[ccxt.Exchange, str],
                 credentials: dict):
        self._exchange_str = exchange
        self._exchange = getattr(
            ccxt, self._exchange_str
        )() if isinstance(self._exchange_str, str) else self._exchange_str
        #self._exchange.urls['api'] = self._exchange.urls['test'] # use the testnet
        
        self._exchange.enableRateLimit = True
        
        self._exchange.apiKey = credentials['apiKey']
        self._exchange.secret = credentials['secret']
        self._base_instrument = USDT; self._quote_instrument = BTC
        
        #self._BTC_USDT_PAIR = TradingPair(USDT, BTC)
        self._DOGE_USDT_PAIR = TradingPair(USDT, DOGE)
        
        self._observation_pairs = [self._DOGE_USDT_PAIR]
        self._observation_symbols = [
            self.pair_to_symbol(pair) for pair in self._observation_pairs
        ]
        self._timeframe = '4h'
        
        self._Obs_DB = pd.DataFrame([], columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        self._exchange.load_markets()
        
        self.ohlcv = self._exchange.fetch_ohlcv(
            self._observation_symbols[0],
            timeframe=self._timeframe,
            limit=1,
        )
        self._f_time = self.ohlcv[0]
                

    def UTC_Time(self):
        now_utc = datetime.now(timezone.utc)
        now_utc = datetime.strftime(now_utc, "%Y-%m-%d %H:00:00")
        return datetime.strptime(now_utc, "%Y-%m-%d %H:00:00")

    def next_observation(self, window_size: int) -> pd.DataFrame:
        self._f_time = self._f_time + timedelta(hours=4)
        self._f_time = datetime.strftime(self._f_time, "%Y-%m-%d %H:00:00")
        self._f_time = datetime.strptime(self._f_time, "%Y-%m-%d %H:00:00")
        print("111111111111111111111111111111111111111111111111111")
        print(type(self._f_time))
        print(self._f_time)
        while self._f_time != self.UTC_Time():
            sleep(1)
            
        temp_dt = self.ohlcv[0]
        self.ohlcv = self._exchange.fetch_ohlcv(
            self._observation_symbols[0],
            timeframe=self._timeframe,
            limit=1,
        )
                
        observations = pd.DataFrame.from_records(self.ohlcv)
        observations.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        observations.loc[0, 'date'] = datetime.utcfromtimestamp(
                observations.loc[0, 'date']/1000
        )
        self._f_time = observations.loc[0, 'date']

        self._Obs_DB = pd.concat(
            [self._Obs_DB, observations],
            ignore_index=True,
            sort=False
        )
        if len(self._Obs_DB) >= window_size:
            observations = self._Obs_DB.iloc[-(window_size):]
        else:
            observations = self._Obs_DB
        return observations

    
    def pair_to_symbol(self, 
                       pair: 'TradingPair') -> str:
        return '{}/{}'.format(pair.quote.symbol, pair.base.symbol)

    def quote_price(self, 
                    pair: 'TradingPair'):
        symbol = self.pair_to_symbol(pair)
        try:
            return float(self._exchange.fetch_ticker(symbol)['close'])
        except BadRequest:
            return np.inf
