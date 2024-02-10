import pandas as pd
from prettytable import PrettyTable
from omspy_brokers.finvasia import Finvasia
from main import load_config_to_list_of_dicts, read_and_get_updated_details, free_margin
from constants import CRED, STGY, logging
from datetime import datetime, timedelta
import time
from tabulate import tabulate


def ohlc_to_ha(df):
    ha_df = pd.DataFrame()
    ha_df["intc"] = (df["into"] + df["inth"] + df["intl"] + df["intc"]) / 4
    ha_df["into"] = ((df["into"] + df["intc"]) / 2).shift(1)
    ha_df["inth"] = df[["inth", "into", "intc"]].max(axis=1)
    ha_df["intl"] = df[["intl", "into", "intc"]].min(axis=1)
    ha_df.loc[0, "into"] = df["into"].iloc[1]
    return ha_df


def get_historical_data(sym_config, broker, interval=1, is_hieken_ashi=False):
    yesterday = datetime.now() - timedelta(days=200)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)
    historical_data: list[dict] | None = broker.historical(
        sym_config["exchange"], sym_config["token"], start_time, None, str(interval)
    )
    if historical_data is not None:
        historical_data_df = pd.DataFrame(historical_data)
        num_columns = ["intc", "intv", "inth", "into", "intl", "intvwap"]
        historical_data_df[num_columns] = historical_data_df[num_columns].apply(
            pd.to_numeric, errors="coerce"
        )
        if not is_hieken_ashi:
            return historical_data_df
        heiken_aishi_df = ohlc_to_ha(historical_data_df)
        return heiken_aishi_df
    return pd.DataFrame()


if __name__ == "__main__":
    configuration_details = load_config_to_list_of_dicts(STGY + "buy_sell_config.csv")
    logging.debug(f"configuration_details: {configuration_details}")

    BROKER = Finvasia
    broker = BROKER(**CRED)
    if broker.authenticate():
        print("login successful")
        MARGIN = free_margin(broker)
    symbols_and_config = read_and_get_updated_details(broker, configuration_details)
    for sym_config in symbols_and_config:
        table = PrettyTable()
        table.field_names = [f"Key", "Value"]
        for key, value in sym_config.items():
            table.add_row([key, value])
        print(table)

        for timeframe in (
            sym_config["intermediate_Candle_timeframe_in_minutes"],
            sym_config["exit_Candle_timeframe_in_minutes"],
        ):
            print("====================Normal=======================")
            df = get_historical_data(
                sym_config, broker, timeframe, is_hieken_ashi=False
            )
            print(tabulate(df.head(5), headers='keys', tablefmt='psql', showindex=False))
            print("====================HA=======================")
            df = get_historical_data(
                sym_config, broker, timeframe, is_hieken_ashi=True
            )
            print(tabulate(df.head(5), headers='keys', tablefmt='psql', showindex=False))

    # print(symbols_and_config)
