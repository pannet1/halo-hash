from toolkit.logger import Logger
from omspy_brokers.bypass import Bypass
import sys
from time import sleep
import traceback
import pendulum
from constants import CRED, STGY, SECDIR, TGRAM, logging, FUTL, CRED_ZERODHA

logging = Logger(10)


FM = pendulum.now().subtract(days=199).to_datetime_string()
print(CRED_ZERODHA)


def get_kite():
    try:
        enctoken = None
        tokpath = SECDIR + CRED_ZERODHA["userid"] + ".txt"
        with open(tokpath, "r") as tf:
            enctoken = tf.read()
            print(f"{tokpath=} has {enctoken=}")
        bypass = Bypass(CRED_ZERODHA["userid"], CRED_ZERODHA["password"],
                        CRED_ZERODHA["totp"], tokpath, enctoken)
        if not bypass.authenticate():
            raise ValueError("unable to authenticate")
        else:
            print(bypass.profile)
    except Exception as e:
        logging.error(f"unable to create bypass object  {e}")
        remove_token()
    else:
        return bypass


def remove_token():
    tokpath = SECDIR + CRED_ZERODHA["userid"] + ".txt"
    with open(tokpath, "w") as tp:
        tp.write("")


broker = get_kite()
to = pendulum.now().to_datetime_string()
data = broker.kite.historical_data("5633", FM, to, "60minute")
print(data)
