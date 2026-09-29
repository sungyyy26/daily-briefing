"""Turn a Meta ads_get_ad_entities campaign-level daily result (JSON file) into
dashboard fact rows keyed by date/line/form. US campaigns only.
Usage: python3 sync/meta_transform.py <meta_result.json> > meta_facts.json"""
import json, re, sys, collections

LINES = {"v": "VIT", "n": "NAD", "b": "BAK"}

def classify(name):
    low = name.lower()
    if "[us]" not in low: return None                       # US only
    if "trio" in low: forms = ["TRIO"]
    m = re.search(r"[\]_ ]([a-z])-(srm|crm|wm)((?:[&+](?:[a-z]-)?(?:srm|crm|wm))*)", low)
    if not m: return ("OTH", "OTH")
    line = LINES.get(m.group(1), "OTH")
    parts = {m.group(2), *re.findall(r"srm|crm|wm", m.group(3))}
    if "trio" in low: form = "TRIO"
    elif parts == {"srm", "crm"}: form = "DUO"
    elif parts == {"srm"}: form = "SRM"
    elif parts == {"crm"}: form = "CRM"
    else: form = "OTH"
    return (line, form)

def num(v):
    if isinstance(v, dict): v = v.get("value")
    try: return float(v)
    except (TypeError, ValueError): return 0.0

def main():
  raw = json.load(open(sys.argv[1]))
  rows = json.loads(raw["ad_entities"]) if isinstance(raw.get("ad_entities"), str) else raw["ad_entities"]
  out = collections.defaultdict(lambda: collections.Counter())
  for r in rows:
      c = classify(r.get("name", ""))
      if not c or "date_start" not in r: continue
      k = (r["date_start"], *c)
      out[k].update({"meta_spend": num(r.get("amount_spent")), "meta_impressions": num(r.get("impressions")),
                     "meta_clicks": num(r.get("clicks")), "meta_purchases": num(r.get("omni_purchase")),
                     "meta_revenue": num(r.get("omni_purchase_values"))})
  facts = [{"id": f"{d}_{l}_{f}", "date": d, "line": l, "form": f, **{k: round(v, 2) for k, v in m.items()}}
           for (d, l, f), m in sorted(out.items())]
  json.dump({"facts": facts, "next_cursor": (raw.get("pagination") or {}).get("next_cursor")}, sys.stdout)


if __name__ == "__main__":
  main()
