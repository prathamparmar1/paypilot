import sys
import uuid
from decimal import Decimal

sys.path.insert(0, ".")
from app.paypal import client as pp

o = pp.create_order(uuid.uuid4(), "TEST-1", "diagnostic", Decimal("1.00"), "USD")
print("order id:", o["id"], "| status:", o["status"])
for l in o["links"]:
    print(l["rel"], l["href"])