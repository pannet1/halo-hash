from omspy_brokers.finvasia import Finvasia
from toolkit.fileutils import Fileutils
from pathlib import Path
import pandas as pd
import datetime
data_from_details = pd.DataFrame()

if __name__ == "__main__":
    current_dir = Path.cwd()
    parent_dir = current_dir.parent
    cred_file_path = parent_dir / "finvasia_creds.yaml"
    cred = Fileutils().get_lst_fm_yml(cred_file_path)
    try:
        finvasia = Finvasia(cred["user_id"], cred["password"], cred["Totp key"], cred["vendor_code"], cred["app_key"], cred["imei"])
        if finvasia.authenticate():
            print("\n successfully authenticated")
    except Exception:
        print("exception .. exiting")
        SystemExit()
    start_timestamp_str = "2023-09-15 00:00:00" 
    end_timestamp_str = "2023-09-16 00:00:00"
    
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    timestamp_datetime = datetime.datetime.strptime(start_timestamp_str, timestamp_format)
    start_epoch_timestamp = timestamp_datetime.timestamp()
    timestamp_datetime = datetime.datetime.strptime(end_timestamp_str, timestamp_format)
    end_epoch_timestamp = timestamp_datetime.timestamp()
    instrument_list = ["BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA"]
    for instrument in instrument_list:
        token = finvasia.instrument_symbol("NSE", instrument)
        api_output = finvasia.historical("NSE", token, start_epoch_timestamp, end_epoch_timestamp)
        api_df = pd.DataFrame(api_output)
        api_df["instrument"] = instrument
        api_df.drop(['stat', 'ssboe','intvwap','intv','intoi','v','oi'], axis=1, inplace=True)
        api_df.rename(columns={'into': 'open', 'inth': 'high', 'intl': 'low', 'intc': 'close'}, inplace=True)
        if not data_from_details.empty:
            data_from_details = pd.concat([data_from_details, api_df], ignore_index=True)
        else:
            data_from_details = api_df

