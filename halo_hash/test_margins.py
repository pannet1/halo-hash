from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia


def free_margin(broker):
    margins = broker.margins
    if isinstance(margins, dict):
        print(margins)
        return int(float(margins.get("cash", 0)))
    return 0.05


SECDIR = "../../"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
BROKER = Finvasia
broker = BROKER(**CRED)
if broker.authenticate():
    print("login successful")
    print("free margin", free_margin(broker))  # free_margin(broker)
