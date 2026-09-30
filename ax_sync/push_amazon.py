"""Run on the AX server (cron, hourly). Queries Amazon sales from the AX MySQL DB,
POSTs product-level daily rows to the dashboard ingest API (no data in git).

Setup:  pip install pymysql
        cp .env.example .env   # fill in values
Cron:   5 * * * * cd /path/to/daily-briefing && python3 ax_sync/push_amazon.py
"""
import json, os, datetime, decimal, pathlib, urllib.request
import pymysql

ROOT = pathlib.Path(__file__).resolve().parent.parent
env_file = ROOT / "ax_sync" / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Edit to match the AX schema (US marketplace only).
# Must return per day per SKU/ASIN: date, sku, sales, units, orders, sessions.
QUERY = os.environ.get("AMAZON_QUERY") or """
SELECT DATE(purchase_date)             AS date,
       asin                            AS sku,
       SUM(item_price)                 AS sales,
       SUM(quantity)                   AS units,
       COUNT(DISTINCT amazon_order_id) AS orders,
       NULL                            AS sessions
FROM amazon_orders
WHERE purchase_date >= CURDATE() - INTERVAL 90 DAY AND marketplace = 'US'
GROUP BY DATE(purchase_date), asin
"""

# SKU/ASIN -> "LINE/FORM" (LINE: VIT NAD BAK, FORM: SRM CRM DUO TRIO). Unlisted -> OTH/OTH.
PRODUCT_MAP = json.loads((ROOT / "ax_sync" / "product_map.json").read_text())

def clean(v):
    if isinstance(v, decimal.Decimal): return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)): return v.isoformat()[:10]
    return v

conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 3306)),
                       user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                       database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
with conn, conn.cursor() as cur:
    cur.execute(QUERY)
    raw = [{k: clean(v) for k, v in r.items()} for r in cur.fetchall()]

agg = {}
for r in raw:
    line, form = PRODUCT_MAP.get(str(r["sku"]), "OTH/OTH").split("/")
    a = agg.setdefault((r["date"], line, form), {"date": r["date"], "line": line, "form": form})
    for k in ("sales", "units", "orders", "sessions"):
        if r.get(k) is not None: a["amz_" + k] = round(a.get("amz_" + k, 0) + float(r[k]), 2)
rows = sorted(agg.values(), key=lambda a: (a["date"], a["line"], a["form"]))

body = json.dumps({"source": "amazon", "updatedAt": datetime.datetime.utcnow().isoformat() + "Z", "facts": rows}).encode()
req = urllib.request.Request(os.environ["INGEST_URL"], body, {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["INGEST_TOKEN"]})
print(urllib.request.urlopen(req, timeout=60).read().decode())
