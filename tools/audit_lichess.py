import sys, json, requests
sys.path.insert(0, r"C:\Users\oriya\klimate-repo")
import data_engine, insights, lichess

user = "drnykterstein"
r = requests.get(f"https://lichess.org/api/games/user/{user}", params={"max": 200, "perfType": "blitz,bullet,rapid"},
                 headers=lichess.HEADERS | {"Accept": "application/x-ndjson"}, stream=True, timeout=60)
raw = [json.loads(l) for l in r.iter_lines() if l]
truth = {}
for g in raw:
    for side in ("white", "black"):
        p = g["players"][side]
        if p.get("user", {}).get("name", "").lower() == user:
            truth[g["id"]] = p.get("ratingDiff")
df = data_engine.fetch_games(user, 200, 0, platform="lichess")
e = insights.enrich_games(df, user)
ids = [u.rsplit("/", 1)[1] for u in df.sort_values(["date_utc"]).url] if "url" in df else []
# enrich sorts by start; map via order of start_utc
d2 = df.copy(); d2["gid"] = d2["url"].str.rsplit("/", n=1).str[1]
d2["true"] = d2["gid"].map(truth)
d2 = d2.sort_values(["start_utc", "date_utc"], kind="stable").reset_index(drop=True)
m = e.reset_index(drop=True).copy()
m["true"] = d2["true"].to_numpy()[: len(m)]
chk = m.dropna(subset=["rating_change", "true"])
chk = chk[chk["rated"]]
print("games", len(m), "checked", len(chk), "exact match", int((chk["rating_change"] == chk["true"]).sum()),
      "max abs err", float((chk["rating_change"] - chk["true"]).abs().max()))



