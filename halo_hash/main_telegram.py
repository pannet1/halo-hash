from omspy_brokers.finvasia import Finvasia
from telethon.sync import TelegramClient, events
import traceback
from constants import CRED, STGY, logger, TGRAM, CRED_TELEGRAM, FUTL
from calculate import entry_quantity
import csv
from datetime import datetime, timedelta, date
import time
import sys
import pandas as pd
import pendulum
import tempfile
from prettytable import PrettyTable

socket_opened = False
import requests
import zipfile
import os
root = 'https://api.shoonya.com/'
masters = ['NSE_symbols.txt.zip', ] 
for zip_file in masters:    
    url = root + zip_file
    r = requests.get(url, allow_redirects=True)
    open(zip_file, 'wb').write(r.content)
    file_to_extract = zip_file.split()

    try:
        with zipfile.ZipFile(zip_file) as z:
            z.extractall()
    except:
        print("Invalid file")
    os.remove(zip_file)
contract_nse_master_data = pd.read_csv('NSE_symbols.txt')[['Exchange','Symbol','Token','LotSize']].to_dict(orient="records")

local_position_book = STGY + "positions.csv"
api_id = CRED_TELEGRAM['api_id']
api_hash = CRED_TELEGRAM['api_hash']
channel_ids = CRED_TELEGRAM['input_channel_id']
HEADERS = "strategy,symbol,exchange,action,intermediate_Candle_timeframe_in_minutes,exit_Candle_timeframe_in_minutes,capital_in_thousand,Risk per trade,Margin required,strategy_entry_time,strategy_exit_time,lot_size,product,token,exchange|token,is_in_position_book,strategy_started,stop_loss,quantity,side,life_cycle_state,last_transaction_time"

client = TelegramClient('anon', api_id, api_hash)

def is_time_reached(time_in_config):
    # check if current time is greater than time as per configuration
    # and return True or False
    entry_time = time_in_config.split(":")
    current_time = pendulum.now(pendulum.timezone("Asia/Kolkata"))
    target_time = current_time.replace(
        hour=int(entry_time[0]), minute=int(entry_time[1]), second=0, microsecond=0
    )
    return False if current_time < target_time else True

def load_config_to_list_of_dicts(csv_file_path):
    """
    output example:
    [
        {'action': 'SELL', 'symbol': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '1'},
        {'action': 'SELL', 'symbol': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '2'},
        {'action': 'BUY', 'symbol': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '3'},
        {'action': 'BUY', 'symbol': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '4'}
        ]
    """
    csv_data = open(csv_file_path).read()
    rows = [row.split(",") for row in csv_data.split("\n") if row]
    headers = [row[0] for row in rows]
    data_rows = [row[1:] for row in rows]
    list_of_dicts = [{} for _ in range(len(rows[0]) - 1)]
    for i in range(len(data_rows[0])):
        for j in range(len(data_rows)):
            list_of_dicts[i][headers[j]] = data_rows[j][i]
    return list_of_dicts

def read_strategies(config) -> list[dict]:
    strategy_name = config["strategy"]
    csv_data = []
    path = f"{STGY}{strategy_name}/short_listed.csv"
    today_date = date.today()
    with open(path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        # Iterate through each row in the CSV file
        for row in csv_reader:
            parsed_date = datetime.strptime(row[0], "%Y-%m-%d").date()
            if parsed_date == today_date:
                dct = dict(strategy=strategy_name,
                           symbol=row[1], exchange=row[2])
                # Append the row as a list to csv_data
                dct.update(config)
                csv_data.append(dct)
    return csv_data

def free_margin(broker):
    margins = broker.margins
    if isinstance(margins, dict):
        logger.info(margins)
        return int(float(margins.get("cash", 0)))
    return 0.05

def event_handler_order_update(message):
    TGRAM.send_msg("order updates: " + str(message))

def open_callback():
    global socket_opened
    socket_opened = True
    print('app is connected')
    # api.subscribe('NSE|11630', feed_type='d')

def get_latest_positions():
    open_positions = []
    with open(local_position_book, "r") as csv_file:
        headers = HEADERS.split(",")
        csv_reader = csv.DictReader(csv_file, fieldnames=headers)
        for row in csv_reader:
            open_positions.append(row)
    consolidated_positions = {}
    for position in open_positions:
        if position["symbol"] not in consolidated_positions:
            consolidated_positions[position["symbol"]] = {k:v for k,v in position.items() if k in ("symbol", "quantity", "life_cycle_state", "action", "last_transaction_time")}
        else:
            dir = 1 if position["side"] == "B" else -1
            consolidated_positions[position["symbol"]]["quantity"] = int(position["quantity"]) * dir
            consolidated_positions[position["symbol"]]["life_cycle_state"] = "Entry" if position.get("life_cycle_state", "False") == "False" else position["life_cycle_state"]   
            consolidated_positions[position["symbol"]]["action"] = position["action"]
            consolidated_positions[position["symbol"]]["last_transaction_time"] = position["last_transaction_time"]
    consolidated_positions = [i for i in list(consolidated_positions.values()) if int(i['quantity']) != 0]
    if consolidated_positions:
        x = PrettyTable()
        column_names = consolidated_positions[0].keys()
        x.field_names = column_names
        for row in consolidated_positions:
            x.add_row(row.values())
        response = '<pre>{}</pre>'.format(x.get_string())
        TGRAM.send_msg(f"Summary:\n\n{response}&parse_mode=HTML")
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_csv:
            writer = csv.DictWriter(temp_csv, fieldnames=column_names)
            writer.writeheader()
            writer.writerows(consolidated_positions)
            temp_csv_name = temp_csv.name
        document = open(temp_csv_name, "rb")
        url = f"https://api.telegram.org/bot{TGRAM.api_key}/sendDocument"
        _ = requests.post(url, data={'chat_id': TGRAM.chat_id}, files={'document': document})
    else:
        TGRAM.send_msg(f"No summary to send")

def is_available_in_position_book(open_positions, config):
    # set this to True sym_config["is_in_position_book"]
    quantity = 0
    desired_position = {}
    life_cycle_state = "False"
    for position in open_positions:
        if config["symbol"] == position["symbol"]:  # Add strategy name here
            dir = 1 if position["side"] == "B" else -1
            quantity += int(position["quantity"]) * dir
    for value in open_positions[::-1]:
        if config["symbol"] == value["symbol"]:  # Add strategy name here
            desired_position = value
            break
    for value in open_positions:
        if config["symbol"] == value["symbol"]:  # Add strategy name here
            if value.get("life_cycle_state", "False") != "False":
                life_cycle_state = value.get("life_cycle_state")
    return (quantity, desired_position, life_cycle_state)

def get_details_for_symbol(symbol, exchange, detail='Token'):
    for entry in contract_nse_master_data:
        if symbol.lower() == entry['Symbol'].lower() and exchange.upper() == entry.get('Exchange', 'NSE'):
            return str(entry[detail])

def remove_exit_all_from_local_position_book():
    with open(local_position_book, "r") as csv_file:
        headers = HEADERS.split(",")
        csv_reader = csv.DictReader(csv_file, fieldnames=headers)
        # Iterate through each row in the CSV file
        positions_ = [r for r in csv_reader]
        for p in positions_.copy():
            if p['life_cycle_state'] == 'EXIT_ALL' and p['last_transaction_time'] != datetime.today().strftime('%d-%m-%Y'):
                for position in positions_:
                    if position['symbol'] == p['symbol']:
                        positions_.remove(position)
        with open(local_position_book, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS.split(","))
            writer.writeheader()
            writer.writerow(positions_)


def read_and_get_updated_details(broker, configuration_details, symbols):
    if not broker.authenticate():
        TGRAM.send_msg("Login Issue! Please check. Exiting now!")
        sys.exit()
    symbols_and_config = []
    for _config in configuration_details:
        logger.info(_config)
        for symbol in symbols:
            config = _config.copy()
            config.update({"symbol":symbol, "exchange": "NSE"})
            logger.info(config)
            symbols_and_config.append(config)
    logger.info(symbols_and_config)

    open_positions = []
    remove_exit_all_from_local_position_book()
    with open(local_position_book, "r") as csv_file:
        headers = HEADERS.split(",")
        csv_reader = csv.DictReader(csv_file, fieldnames=headers)
        # Iterate through each row in the CSV file
        for row in csv_reader:
            logger.info(f"row in position book {row}")
            open_positions.append(row)
    logger.info("=====Open Positions - Start======")
    for pos in open_positions:
        logger.info(pos)
    logger.info("=====Open Positions - End========")
    # Check for today's shortlisted symbols
    for i, sym_config in enumerate(symbols_and_config):
        sym_config["token"] = get_details_for_symbol(sym_config["symbol"], sym_config["exchange"], detail="Token")
        logger.debug(f"token: {sym_config['token']}")
        if not sym_config["token"]:
            sym_config["token"] = broker.instrument_symbol(
                sym_config["exchange"], sym_config["symbol"]
            )
        logger.debug(f"token: {sym_config['token']}")
        sym_config["exchange|token"] = (
            sym_config["exchange"] + "|" + sym_config["token"]
        )
        # https://github.com/Shoonya-Dev/ShoonyaApi-py?tab=readme-ov-file#-get_quotesexchange-token
        sym_config["lot_size"] = get_details_for_symbol(sym_config["symbol"], sym_config["exchange"], detail="LotSize")
        if not sym_config["lot_size"]:
            sym_config["lot_size"] = broker.scriptinfo(
                sym_config["exchange"], sym_config["token"]).get("ls")
        quantity, position, life_cycle_state = is_available_in_position_book(
            open_positions, sym_config
        )
        if position:  # available in position book
            symbols_and_config[i].update(position)
            symbols_and_config[i]["quantity"] = quantity
            symbols_and_config[i]["life_cycle_state"] = life_cycle_state
            symbols_and_config[i]["last_transaction_time"] = position.get("last_transaction_time")
            symbols_and_config[i]["is_in_position_book"] = "True"
        else:
            symbols_and_config[i]["life_cycle_state"] = "False"
            symbols_and_config[i]["last_transaction_time"] = "01-01-2024"
            symbols_and_config[i]["is_in_position_book"] = "False"
    # Check for older shortlisted symbols to manage
    for pos in open_positions:
        if (pos["strategy"], pos["symbol"]) not in [(i["strategy"], i["symbol"]) for i in symbols_and_config]:
            quantity, position, life_cycle_state = is_available_in_position_book(
                open_positions, {"symbol": pos["symbol"]}
            )
            if position and quantity != 0:  # available in position book
                sym_config = {"symbol": pos["symbol"]}
                sym_config["token"] = broker.instrument_symbol(
                    pos["exchange"], pos["symbol"]
                )
                logger.debug(f"token: {sym_config['token']}")
                sym_config["exchange|token"] = (
                    pos["exchange"] + "|" + pos["token"]
                )
                sym_config.update(position)
                sym_config["quantity"] = quantity
                sym_config["life_cycle_state"] = life_cycle_state
                sym_config["last_transaction_time"] = position.get("last_transaction_time")
                symbols_and_config.append(sym_config)

    symbols_and_config = [config for config in symbols_and_config if config["last_transaction_time"] != datetime.today().strftime('%d-%m-%Y')]

    logger.info("=====Updated symbols_and_config - Start======")
    for pos in symbols_and_config:
        logger.info(pos)
    logger.info("=====Updated symbols_and_config - End========")
    return symbols_and_config

def is_order_completed(broker, order_id: str):
    orders = broker.orders
    for order in orders:
        if any(order) and \
                order.get("order_id", "") == order_id and \
                order.get("status", "") == "COMPLETE":
            return True
    return False

def save_to_local_position_book(content_to_save):
    with open(local_position_book, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS.split(","))
        writer.writerow(content_to_save)

def place_order_and_save_to_position_book(args, sym_config):
    TGRAM.send_msg(args)
    if not broker.authenticate():
        TGRAM.send_msg("Login Issue! Please check. Exiting now!")
        sys.exit()
    resp = broker.order_place(**args)
    TGRAM.send_msg(resp if resp else "Got None from Broker")
    logger.debug(resp)
    if resp and is_order_completed(broker, resp):
        sym_config["is_in_position_book"] = "True"
        sym_config["side"] = args["side"]
        sym_config["quantity"] = args["quantity"]
        sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
        sym_config["life_cycle_state"] = args["tag"]
        save_to_local_position_book(sym_config)

def ohlc_to_ha(df):
    df = df[::-1]
    heikin_ashi_df = pd.DataFrame(index=df.index.values, columns=[
                                  'into', 'inth', 'intl', 'intc'])
    heikin_ashi_df['intc'] = (
        df['into'] + df['inth'] + df['intl'] + df['intc']) / 4
    for i in range(len(df)):
        if i == 0:
            heikin_ashi_df.iat[0, 0] = df['into'].iloc[0]
        else:
            heikin_ashi_df.iat[i, 0] = (
                heikin_ashi_df.iat[i-1, 0] + heikin_ashi_df.iat[i-1, 3]) / 2
    heikin_ashi_df['inth'] = heikin_ashi_df.loc[:, [
        'into', 'intc']].join(df['inth']).max(axis=1)
    heikin_ashi_df['intl'] = heikin_ashi_df.loc[:, [
        'into', 'intc']].join(df['intl']).min(axis=1)
    heikin_ashi_df = heikin_ashi_df[::-1]
    return heikin_ashi_df

def get_historical_data(sym_config, interval=1, is_hieken_ashi=False):
    yesterday = datetime.now() - timedelta(days=200)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)
    if not broker.authenticate():
        TGRAM.send_msg("Login Issue! Please check. Exiting now!")
        sys.exit()
    historical_data: list[dict] | None = broker.historical(
        sym_config["exchange"], sym_config["token"], start_time, None, str(
            interval)
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

def manage_strategy(symbols, action):
    symbols_and_config = read_and_get_updated_details(
            broker, configuration_details, symbols)
    logger.info(symbols_and_config)
    for symbol in symbols:
        logger.info(f"Checking {symbol=}")
        try:
            sym_config = [config for config in symbols_and_config if config["symbol"] == symbol][0]
        except IndexError:
            continue
        logger.info(sym_config)
        if "quantity" in sym_config and sym_config["quantity"] == 0:
            continue
        if "last_transaction_time" in sym_config and sym_config["last_transaction_time"] == datetime.today().strftime('%d-%m-%Y'):
            continue
        if action == "EXIT_ALL" and "quantity" in sym_config:
            args = dict(
                side="S" if sym_config["action"] == "B" else "B",   # Buy if sell, sell if bought
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=sym_config["quantity"],
                disclosed_quantity=sym_config["quantity"],
                order_type="MKT",
                symbol=sym_config["symbol"],
                tag="EXIT_ALL",
            )
            place_order_and_save_to_position_book(args, sym_config)
        elif action == "EXIT_50"  and "quantity" in sym_config and (sym_config['life_cycle_state']=='False' or sym_config['life_cycle_state']=='REENTER'):
            exit_quantity = int(int(sym_config["quantity"]) / 2)
            if exit_quantity == 0:
                logger.info("Quantity is 0, hence ignoring")
                continue
            args = dict(
                side="S" if sym_config["action"] == "B" else "B",  # since exiting, B will give S
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                tag="EXIT_50",
            )
            place_order_and_save_to_position_book(args, sym_config)
        elif action == "REENTER"  and "quantity" in sym_config and sym_config['life_cycle_state']!='False' and sym_config['life_cycle_state']=='EXIT_50':
            args = dict(
                side=sym_config["action"],  # since reenter, B will give B
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                tag="REENTER",
            )
            place_order_and_save_to_position_book(args, sym_config)
        elif action == "ENTRY":
            # if sym_config.get("is_in_position_book", "False") == "True":
            #     continue
            historical_data_df = get_historical_data(sym_config, 1)
            if historical_data_df.empty:
                continue
            historical_data_df = historical_data_df.iloc[1:11]
            if sym_config["action"] == "S":
                last_10_candles = float(historical_data_df["inth"].max())
            else:
                last_10_candles = float(historical_data_df["intl"].min())
            if not broker.authenticate():
                TGRAM.send_msg("Login Issue! Please check. Exiting now!")
                sys.exit()
            ltp = float(broker.scriptinfo(sym_config["exchange"], sym_config["token"]).get("lp")) # TODO: get ltp here
            calc = dict(
                last_10_candles=last_10_candles,
                ltp=ltp,
                side=sym_config["action"],
            )
            calc.update(sym_config)
            quantity, stop_loss = entry_quantity(**calc)
            sym_config["stop_loss"] = stop_loss
            if quantity == 0:
                continue
            args = dict(
                side=sym_config["action"],
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=quantity,
                disclosed_quantity=quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                tag="False",
            )
            place_order_and_save_to_position_book(args, sym_config)

@client.on(events.NewMessage(chats=channel_ids))
async def my_event_handler(event):
    msg = event.raw_text
    if "Extra Data:" in msg:
        try:
            intended_msg_list = msg.split("Extra Data:")[1].split(",")
            symbol_shortlisted = [symbol.split(" - ")[0].strip() for symbol in intended_msg_list if "-" in symbol]
            if "Re enter" in intended_msg_list[0]:
                manage_strategy(symbol_shortlisted, "REENTER")
            elif "Full exit" in intended_msg_list[0]:
                manage_strategy(symbol_shortlisted, "EXIT_ALL")
            elif '50% exit' in intended_msg_list[0]:
                manage_strategy(symbol_shortlisted, "EXIT_50")
            elif "Entry" in intended_msg_list[0]:
                manage_strategy(symbol_shortlisted, "ENTRY")
            else:
                logger.debug(f"Ignoring msg : {msg}")
        except:
            logger.error(traceback.format_exc())
    elif "stop algo" in msg.lower():
        TGRAM.send_msg("Stop algo command received! Exiting now!")
        get_latest_positions()
        sys.exit()
    else:
        logger.debug(f"Ignoring msg : {msg}")
    if is_time_reached('15:30'):
        TGRAM.send_msg("Logout time reached! Exiting now!")
        get_latest_positions()
        sys.exit()
    logger.debug(f"Waiting for next message...")

if __name__ == "__main__":
    global broker, configuration_details
    configuration_details = load_config_to_list_of_dicts(
        STGY + "buy_sell_config.csv")
    logger.debug(f"configuration_details: {configuration_details}")

    BROKER = Finvasia
    broker = BROKER(**CRED)
    if broker.authenticate():
        logger.info("login successful")
        ret = broker.finvasia.start_websocket(order_update_callback=event_handler_order_update, socket_open_callback=open_callback)
        MARGIN = free_margin(broker)
    
        # Read telegram messages
        try:
            client.start(phone=CRED_TELEGRAM["phone_number"])
            client.run_until_disconnected()
        except:
            pass
