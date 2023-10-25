import time
from datetime import datetime, timedelta
import pandas as pd


class Wserver:
    exchsym = []
    ticks = {}
    feed_opened = False

    def __init__(self, broker):
        self.api = broker.finvasia
        self.api.start_websocket(
            order_update_callback=self.order_update_cb,
            subscribe_callback=self.subscribe_cb,
            socket_open_callback=self.socket_open_cb,
        )

    def order_update_cb(self, cb):
        pass
        # print(cb)

    def subscribe_cb(self, tick):
        if isinstance(tick, dict):
            if tick["e"] == "NSE":
                self.ticks[tick["ts"][:-3]] = float(tick["lp"])
            else:
                self.ticks[tick["ts"]] = float(tick["lp"])

    def socket_open_cb(self):
        self.feed_opened = True

    def not_implemented(self, es):
        if isinstance(es, list):
            self.exchsym.extend(es)
        else:
            self.exchsym.append(es)

    def ltp(self, lst):
        if not isinstance(lst, list):
            lst = [lst]
        tkns = []
        for k in lst:
            v = k.split(":")
            if v[0] == "NSE":
                v[1] = v[1] + "-EQ"
            resp = self.api.searchscrip(exchange=v[0], searchtext=v[1])
            if resp:
                tkn = resp["values"][0]["token"]
                tkns.append(v[0] + "|" + tkn)
        if any(tkns):
            self.api.subscribe(tkns)
            while not any(self.ticks):
                time.sleep(0.2)
            else:
                return self.ticks

    def close(self):
        self.api.close_websocket()


if __name__ == "__main__":
    from omspy_brokers.finvasia import Finvasia
    import yaml

    BROKER = Finvasia
    dir_path = "../../"
    with open(dir_path + "config2.yaml", "r") as f:
        config = yaml.safe_load(f)["finvasia"]
        print(config)
        broker = BROKER(**config)
        if broker.authenticate():
            print("success")
    # init only once
    ws = Wserver(broker)

    while True:
        instrument_names = ["NSE:INFY", "NSE:TRIDENT"]
        resp = ws.ltp(instrument_names)
        print(resp)
        for inst in instrument_names:
            e, s = inst.split(":")
            a = broker.instrument_symbol(e, s)
            print(a)
            yesterday = datetime.now() - timedelta(days=6)
            yesterday_time_string = yesterday.strftime(
                '%d-%m-%Y') + ' 00:00:00'
            time_obj = time.strptime(
                yesterday_time_string, '%d-%m-%Y %H:%M:%S')
            start_time = time.mktime(time_obj)
            today = datetime.now()
            today_time_string = today.strftime('%d-%m-%Y %H:%M:%S')
            time_obj = time.strptime(today_time_string, '%d-%m-%Y %H:%M:%S')
            end_time = time.mktime(time_obj)
            print(start_time, end_time)
            historical_data: list[dict] | None = broker.historical(
                e, a, start_time, end_time)
            if historical_data is not None:
                df = pd.DataFrame(historical_data[1:11])

                print(df)
        break
    # print(resp)
    # ws.close()
    # Add a delay or perform other operations here

    # When done, close the WebSocket connection
