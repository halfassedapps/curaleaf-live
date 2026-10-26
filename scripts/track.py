"""Daily first-seen tracker for Curaleaf PA flower menus.

For each store, records the date each product (key "brand||name type", same as
index.html) first appears. data/firstseen-<id>.json:
  base:  date tracking began for that store
  known: products already on the menu at base (shown as "by <base>")
  first: product -> date first seen after base
A store whose menu can't be fetched completely is skipped for the day.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://web-ui-curaleaf.sweedpos.com/_api/proxy/Products/GetProductList"
STORES = ["145", "146", "147", "148", "149", "150", "151", "152", "153",
          "154", "155", "156", "157", "158", "159", "160", "161", "162"]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def post(store, page):
    body = json.dumps({"pageSize": 400, "page": page, "filters": {"category": [1287]},
                       "sortingMethodId": 1, "saleType": "Medical", "platformOs": "web"}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json", "storeid": store,
        "user-agent": "Mozilla/5.0 (curaleaf-live tracker)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)


def menu_keys(store):
    items, page, total = [], 1, None
    while True:
        j = post(store, page)
        total = j.get("total") or 0
        batch = j.get("list") or []
        items += batch
        if len(items) >= total or not batch:
            break
        page += 1
    if not items or len(items) < total:
        raise RuntimeError(f"incomplete menu: {len(items)} of {total}")
    keys = set()
    for it in items:
        pt = (it.get("productType") or {}).get("name") or ""
        brand = (it.get("brand") or {}).get("name") or ""
        keys.add(brand + "||" + (it["name"] + " " + pt).strip())
    return keys


def main():
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    failed = []
    for store in STORES:
        path = os.path.join(DATA, f"firstseen-{store}.json")
        try:
            keys = menu_keys(store)
        except Exception as e:
            print(f"{store}: FAILED {e}")
            failed.append(store)
            continue
        if os.path.exists(path):
            with open(path) as f:
                fs = json.load(f)
            seen = set(fs["known"]) | set(fs["first"])
            new = sorted(keys - seen)
            for k in new:
                fs["first"][k] = today
            print(f"{store}: {len(keys)} on menu, {len(new)} new")
        else:
            fs = {"base": today, "known": sorted(keys), "first": {}}
            print(f"{store}: {len(keys)} on menu, tracking starts {today}")
        fs["known"] = sorted(fs["known"])
        with open(path, "w") as f:
            json.dump(fs, f, indent=0, sort_keys=True)
            f.write("\n")
    if len(failed) == len(STORES):
        sys.exit("all stores failed")


if __name__ == "__main__":
    main()
