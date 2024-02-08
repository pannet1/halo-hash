from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia
import pandas as pd
from pprint import pprint

SECDIR = "../../"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]

BROKER = Finvasia
broker = BROKER(**CRED)
if broker.authenticate():
    print("login successful")
else:
    print("unable to login exiting")
    SystemExit(1)

args = dict(
    side="S",
    product="C",  #  for NRML
    exchange="NSE",
    quantity=0,
    disclosed_quantity=0,
    order_type="MKT",
    symbol="TRIDENT",
    # price=prc, # in case of LMT order
    tag="manual order",
)


def get_holdings():
    try:
        resp = broker.finvasia.get_holdings("C")
        if resp and any(resp):
            flattened_list = []

            for nested_dict in resp:
                flattened_dict = {
                    "exch": nested_dict["exch_tsym"][0]["exch"],
                    "tsym": nested_dict["exch_tsym"][0]["tsym"],
                    "token": nested_dict["exch_tsym"][0]["token"],
                    "holdqty": nested_dict["holdqty"],
                    "prd": nested_dict["prd"],
                    "sell_amt": nested_dict["sell_amt"],
                    "trdqty": nested_dict["trdqty"],
                    "upldprc": nested_dict["upldprc"],
                    "usedqty": nested_dict["usedqty"],
                }
                flattened_list.append(flattened_dict)
            df_pos = pd.DataFrame(flattened_list)
            df_print = df_pos
            print(df_print)
            return df_pos
    except Exception as e:
        print(e)
        raise


def get_positions():
    try:
        df_pos = pd.DataFrame(broker.positions)

        if df_pos is not None and not df_pos.empty:
            df_pos = df_pos[
                [
                    "symbol",
                    "exchange",
                    "prd",
                    "token",
                    "ti",
                    "quantity",
                    "urmtom",
                    "rpnl",
                    "last_price",
                ]
            ]
            df_print = df_pos.drop(
                ["exchange", "prd", "token", "ti"], axis=1
            ).set_index("symbol")
            print(df_print)
            return df_pos
    except Exception as e:
        print(e)
        raise


def get_orders():
    try:
        df_ord = pd.DataFrame(broker.orders)
        if df_ord is not None and not df_ord.empty:
            df_ord = df_ord[
                [
               "broker_timestamp",
                "symbol",
                "side",
                "average_price",
                "status",
                "filled_quantity",
                "rejreason",
                "remarks"
                ]
            ]
            df_print = df_ord.set_index("symbol")
            print(df_print)
            return df_ord
        return pd.DataFrame()
    except Exception as e:
        print(e)
        raise


get_holdings()
get_positions()
get_orders()
# resp = broker.order_place(**args)
# print(resp)

# cancel order

