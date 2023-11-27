from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia


SECDIR = "../../"
FUTL = Fileutils()
CONFIG = FUTL.get_lst_fm_yml(SECDIR + "halo-hash.yml")
CRED = CONFIG["finvasia"]
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

order_id = "23112700009362"

BROKER = Finvasia
broker = BROKER(**CRED)
if broker.authenticate():
    print("login successful")
    
    # resp = broker.order_place(**args)
    # print(resp)

    # cancel order
    resp = broker.order_cancel(order_id)
    print(resp)
