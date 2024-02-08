import pandas as pd
from time import sleep


df = pd.read_csv('data/PFC.csv', index_col='time', parse_dates=True)
ohlc = {
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}
print(df.tail())
df = df.resample('1H', origin='start').apply(ohlc)
df = df.drop(df[df.open.isnull()].index)
print(df.head(5))
print(df.tail())
sleep(5)
