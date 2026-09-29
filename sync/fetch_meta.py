"""GitHub Action: pull Meta Ads campaign insights (daily, last 35 days) with the
System User token, classify by product, and POST to the dashboard's ingest API.
Env: META_TOKEN, META_AD_ACCOUNT, INGEST_URL, INGEST_TOKEN, [META_API_VERSION]"""
import json, os, sys, datetime, urllib.request, urllib.parse, collections
sys.path.insert(0, os.path.dirname(__file__))
from meta_transform import classify

ver = os.environ.get("META_API_VERSION", "v23.0")
today = datetime.date.today()
params = {"level": "campaign", "time_increment": "1", "limit": "500",
          "fields": "campaign_name,spend,impressions,clicks,actions,action_values",
          "time_range": json.dumps({"since": str(today - datetime.timedelta(days=35)), "until": str(today)}),
          "access_token": os.environ["META_TOKEN"]}
url = f"https://graph.facebook.com/{ver}/act_{os.environ['META_AD_ACCOUNT']}/insights?" + urllib.parse.urlencode(params)

def pick(lst, types=("omni_purchase", "purchase")):
    d = {a["action_type"]: float(a["value"]) for a in lst or []}
    return next((d[t] for t in types if t in d), 0.0)

out = collections.defaultdict(collections.Counter)
while url:
    page = json.load(urllib.request.urlopen(url, timeout=60))
    for r in page.get("data", []):
        c = classify(r.get("campaign_name", ""))
        if not c: continue
        out[(r["date_start"], *c)].update({"meta_spend": float(r.get("spend", 0)), "meta_impressions": float(r.get("impressions", 0)),
            "meta_clicks": float(r.get("clicks", 0)), "meta_purchases": pick(r.get("actions")), "meta_revenue": pick(r.get("action_values"))})
    url = page.get("paging", {}).get("next")

facts = [{"date": d, "line": l, "form": f, **{k: round(v, 2) for k, v in m.items()}} for (d, l, f), m in sorted(out.items())]
body = json.dumps({"source": "meta", "updatedAt": datetime.datetime.utcnow().isoformat() + "Z", "facts": facts}).encode()
req = urllib.request.Request(os.environ["INGEST_URL"], body, {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["INGEST_TOKEN"]})
print(urllib.request.urlopen(req, timeout=60).read().decode(), len(facts), "facts")
