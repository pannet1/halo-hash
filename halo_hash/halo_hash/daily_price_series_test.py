from constants import CRED
from omspy_brokers.finvasia import Finvasia
import pendulum


def login_and_get_token():
    try:
        api = Finvasia(**CRED)
        if api.login():
            print("Login Successfull")
            return api
    except Exception as e:
        print(e)


api = login_and_get_token()


def unixtime(timee):
    return pendulum.from_format(timee, 'DDMMYYYY HH:mm:ss').timestamp()


st = unixtime('01092023 09:15:00')
et = unixtime('23092023 15:30:00')

re = api.get_daily_price_series(
    exchange='NSE', tradingsymbol='PFC', startdate=st, enddate=et)
print(re)
