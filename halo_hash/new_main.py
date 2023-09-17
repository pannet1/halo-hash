from omspy_brokers.finvasia import Finvasia
from toolkit.fileutils import Fileutils
from pathlib import Path


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
    import datetime
    start_timestamp_str = "2023-09-01 15:30:45" 
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    timestamp_datetime = datetime.datetime.strptime(start_timestamp_str, timestamp_format)
    start_epoch_timestamp = timestamp_datetime.timestamp()
    timestamp_datetime = datetime.datetime.strptime("2023-09-17 15:30:45", timestamp_format)
    end_epoch_timestamp = timestamp_datetime.timestamp()
    token = finvasia.instrument_symbol("NSE", "APOLLO")
    print(token)
    print(finvasia.historical("NSE", token, start_epoch_timestamp, end_epoch_timestamp))


