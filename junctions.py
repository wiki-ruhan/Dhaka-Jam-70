"""৭০টি মোড়ের বিশ্লেষণ / Junction analysis for 70 Dhaka intersections.

1. prepare()  (একবার, init জবে): OpenStreetMap থেকে প্রতিটি মোড়ের আসল অবস্থান আর চারদিকের রাস্তা (leg) বের করে
   data/junctions_osm.json ও data/junctions_exact.csv-এ রাখে। OSM না পেলে আনুমানিক অবস্থান ও ৮ দিকের সোজা রেখা ব্যবহার হয়।
2. measure()  (প্রতি স্লটে): রঙের মানচিত্র থেকে প্রতিটি মোড়ের স্কোর, প্রতিটি দিকের রাস্তার স্কোর, জ্যামের দৈর্ঘ্য
   (মোড় থেকে কত মিটার টানা লাল), আর পাশের মোড় পর্যন্ত জ্যাম পৌঁছেছে কি না মাপে।

Traffic drives on the LEFT in Bangladesh: walking outward from a junction, vehicles coming TOWARD the junction
(the queue) are on the right-hand side of the road, vehicles leaving are on the left-hand side.
"""
import csv
import json
import math
import time
from pathlib import Path

import numpy as np

import config

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OSM_FILE = DATA / "junctions_osm.json"
EXACT_CSV = DATA / "junctions_exact.csv"

# corridor, English name, Bangla name, approximate lat, lng (refined from OpenStreetMap by prepare())
JUNCTIONS = [
    ("North / Airport Road", "Abdullahpur", "আব্দুল্লাহপুর", 23.8797, 90.4006),
    ("North / Airport Road", "Tongi Bridge", "টঙ্গী ব্রিজ", 23.8865, 90.4012),
    ("North / Airport Road", "House Building (Uttara)", "হাউস বিল্ডিং (উত্তরা)", 23.8737, 90.4004),
    ("North / Airport Road", "Azampur", "আজমপুর", 23.8668, 90.4008),
    ("North / Airport Road", "Jasimuddin (Uttara)", "জসীমউদ্দীন (উত্তরা)", 23.8610, 90.4000),
    ("North / Airport Road", "Airport", "বিমানবন্দর", 23.8510, 90.4080),
    ("North / Airport Road", "Kawla", "কাওলা", 23.8450, 90.4110),
    ("North / Airport Road", "Khilkhet", "খিলক্ষেত", 23.8296, 90.4198),
    ("North / Airport Road", "Kuril Bishwa Road", "কুড়িল বিশ্বরোড", 23.8205, 90.4210),
    ("North / Airport Road", "Bashundhara Gate", "বসুন্ধরা গেট (যমুনা ফিউচার পার্ক)", 23.8130, 90.4240),
    ("Banani-Mohakhali-Tejgaon", "Kakoli (Banani)", "কাকলী (বনানী)", 23.7990, 90.4008),
    ("Banani-Mohakhali-Tejgaon", "Amtoli", "আমতলী", 23.7800, 90.3990),
    ("Banani-Mohakhali-Tejgaon", "Mohakhali", "মহাখালী", 23.7781, 90.4050),
    ("Banani-Mohakhali-Tejgaon", "Jahangir Gate", "জাহাঙ্গীর গেট", 23.7770, 90.3930),
    ("Banani-Mohakhali-Tejgaon", "Nabisco (Tejgaon)", "নাবিস্কো (তেজগাঁও)", 23.7705, 90.3995),
    ("Banani-Mohakhali-Tejgaon", "Bijoy Sarani", "বিজয় সরণি", 23.7650, 90.3890),
    ("Banani-Mohakhali-Tejgaon", "Satrasta", "সাতরাস্তা", 23.7575, 90.4000),
    ("Banani-Mohakhali-Tejgaon", "Farmgate", "ফার্মগেট", 23.7577, 90.3897),
    ("Banani-Mohakhali-Tejgaon", "Karwan Bazar", "কারওয়ান বাজার", 23.7510, 90.3930),
    ("Banani-Mohakhali-Tejgaon", "Bangla Motor", "বাংলামোটর", 23.7465, 90.3950),
    ("Gulshan-Badda-Rampura", "Gulshan-1", "গুলশান-১", 23.7808, 90.4167),
    ("Gulshan-Badda-Rampura", "Gulshan-2", "গুলশান-২", 23.7945, 90.4142),
    ("Gulshan-Badda-Rampura", "Notun Bazar", "নতুন বাজার", 23.7980, 90.4235),
    ("Gulshan-Badda-Rampura", "Shahjadpur", "শাহজাদপুর", 23.7915, 90.4245),
    ("Gulshan-Badda-Rampura", "Uttar Badda", "উত্তর বাড্ডা", 23.7860, 90.4260),
    ("Gulshan-Badda-Rampura", "Merul Badda", "মেরুল বাড্ডা", 23.7730, 90.4250),
    ("Gulshan-Badda-Rampura", "Rampura Bridge", "রামপুরা ব্রিজ", 23.7660, 90.4230),
    ("Gulshan-Badda-Rampura", "Malibagh", "মালিবাগ", 23.7495, 90.4125),
    ("Gulshan-Badda-Rampura", "Mouchak", "মৌচাক", 23.7470, 90.4110),
    ("Gulshan-Badda-Rampura", "Moghbazar", "মগবাজার", 23.7490, 90.4040),
    ("Gulshan-Badda-Rampura", "Khilgaon", "খিলগাঁও", 23.7510, 90.4300),
    ("Mirpur-Gabtoli-Aminbazar", "Aminbazar Bridge", "আমিনবাজার ব্রিজ", 23.7880, 90.3230),
    ("Mirpur-Gabtoli-Aminbazar", "Gabtoli", "গাবতলী", 23.7840, 90.3440),
    ("Mirpur-Gabtoli-Aminbazar", "Technical", "টেকনিক্যাল", 23.7835, 90.3530),
    ("Mirpur-Gabtoli-Aminbazar", "Mirpur-1", "মিরপুর-১", 23.7980, 90.3530),
    ("Mirpur-Gabtoli-Aminbazar", "Mirpur-2", "মিরপুর-২", 23.8060, 90.3630),
    ("Mirpur-Gabtoli-Aminbazar", "Mirpur-10", "মিরপুর-১০", 23.8069, 90.3687),
    ("Mirpur-Gabtoli-Aminbazar", "Mirpur-11", "মিরপুর-১১", 23.8165, 90.3665),
    ("Mirpur-Gabtoli-Aminbazar", "Mirpur-12", "মিরপুর-১২", 23.8270, 90.3640),
    ("Mirpur-Gabtoli-Aminbazar", "Kazipara", "কাজীপাড়া", 23.7975, 90.3726),
    ("Mirpur-Gabtoli-Aminbazar", "Shewrapara", "শেওড়াপাড়া", 23.7915, 90.3755),
    ("Mirpur-Gabtoli-Aminbazar", "Agargaon", "আগারগাঁও", 23.7780, 90.3790),
    ("Dhanmondi-Mohammadpur", "Shyamoli", "শ্যামলী", 23.7740, 90.3655),
    ("Dhanmondi-Mohammadpur", "Shia Masjid (Mohammadpur)", "শিয়া মসজিদ (মোহাম্মদপুর)", 23.7675, 90.3625),
    ("Dhanmondi-Mohammadpur", "Mohammadpur Town Hall", "মোহাম্মদপুর টাউন হল", 23.7605, 90.3610),
    ("Dhanmondi-Mohammadpur", "Asad Gate", "আসাদগেট", 23.7600, 90.3740),
    ("Dhanmondi-Mohammadpur", "Dhanmondi 27", "ধানমন্ডি ২৭", 23.7560, 90.3750),
    ("Dhanmondi-Mohammadpur", "Russell Square (Panthapath)", "রাসেল স্কয়ার (পান্থপথ)", 23.7515, 90.3795),
    ("Dhanmondi-Mohammadpur", "Science Lab", "সায়েন্স ল্যাব", 23.7389, 90.3830),
    ("Dhanmondi-Mohammadpur", "Jigatola", "জিগাতলা", 23.7395, 90.3740),
    ("Dhanmondi-Mohammadpur", "Nilkhet", "নীলক্ষেত", 23.7330, 90.3870),
    ("Dhanmondi-Mohammadpur", "Azimpur", "আজিমপুর", 23.7270, 90.3860),
    ("Central", "Shahbag", "শাহবাগ", 23.7383, 90.3958),
    ("Central", "TSC (Dhaka University)", "টিএসসি (ঢাকা বিশ্ববিদ্যালয়)", 23.7335, 90.3963),
    ("Central", "Kakrail", "কাকরাইল", 23.7375, 90.4080),
    ("Central", "Shantinagar", "শান্তিনগর", 23.7400, 90.4140),
    ("Central", "Paltan", "পল্টন", 23.7330, 90.4120),
    ("Central", "Fakirapool", "ফকিরাপুল", 23.7335, 90.4165),
    ("Central", "Gulistan (Zero Point)", "গুলিস্তান (জিরো পয়েন্ট)", 23.7240, 90.4125),
    ("Central", "Shapla Chattar (Motijheel)", "শাপলা চত্বর (মতিঝিল)", 23.7290, 90.4190),
    ("Central", "Kamalapur", "কমলাপুর", 23.7320, 90.4260),
    ("Central", "Ittefaq Mor", "ইত্তেফাক মোড়", 23.7220, 90.4220),
    ("South / Old Dhaka", "Bakshibazar", "বকশিবাজার মোড়", 23.7240, 90.3925),
    ("South / Old Dhaka", "Chankharpul", "চানখারপুল", 23.7230, 90.3990),
    ("South / Old Dhaka", "Nayabazar", "নয়াবাজার", 23.7145, 90.4045),
    ("South / Old Dhaka", "Babubazar Bridge", "বাবুবাজার ব্রিজ", 23.7060, 90.4010),
    ("South / Old Dhaka", "Sadarghat (Bahadur Shah Park)", "সদরঘাট (বাহাদুর শাহ পার্ক)", 23.7085, 90.4120),
    ("South / Old Dhaka", "Sayedabad", "সায়েদাবাদ", 23.7175, 90.4280),
    ("South / Old Dhaka", "Jatrabari", "যাত্রাবাড়ী", 23.7104, 90.4347),
    ("South / Old Dhaka", "Postogola", "পোস্তগোলা", 23.6930, 90.4280),
]

ROAD_CLASSES = {"motorway": 5, "trunk": 5, "primary": 4, "secondary": 3, "tertiary": 2, "unclassified": 1,
                "motorway_link": 1, "trunk_link": 1, "primary_link": 1, "secondary_link": 1, "tertiary_link": 1}
ELEVATED_WORDS = ("flyover", "expressway", "elevated", "ফ্লাইওভার", "এক্সপ্রেসওয়ে", "উড়াল")
COMPASS8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


# ---------------------------------------------------------------- geometry helpers
def _xy(lat, lng, lat0, lng0):
    """Local metres east/north of (lat0, lng0)."""
    return ((lng - lng0) * 111320 * math.cos(math.radians(lat0)), (lat - lat0) * 110574)


def _ll(x, y, lat0, lng0):
    return (lat0 + y / 110574, lng0 + x / (111320 * math.cos(math.radians(lat0))))


def _bearing(p, q):
    """Compass bearing (0 = north, 90 = east) from point p to q, both (x, y) metres."""
    return (math.degrees(math.atan2(q[0] - p[0], q[1] - p[1])) + 360) % 360


def _angle_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def compass8(b):
    return COMPASS8[int((b % 360) / 45 + 0.5) % 8]


def _point_at(poly, dist):
    """Point at a distance along a polyline of (x, y) metres."""
    run = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if run + seg >= dist and seg > 0:
            t = (dist - run) / seg
            return x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        run += seg
    return poly[-1]


def _length(poly):
    return sum(math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(poly, poly[1:]))


# ---------------------------------------------------------------- OpenStreetMap
PREP_BUDGET_S = 420     # সর্বোচ্চ 7 মিনিট; এর বেশি লাগলে বাকি মোড়গুলো সোজা রেখায় মাপা হয়


def _log(msg):
    """Progress straight to the GitHub log (stderr is shown live even when stdout goes to a file)."""
    import sys
    print(msg, file=sys.stderr, flush=True)


def _overpass_area(pad_deg=0.02):
    """All major roads of the whole study area in ONE request (instead of one request per junction)."""
    import requests
    b = config.BOUNDS
    s, w, n, e = b["south"] - pad_deg, b["west"] - pad_deg, b["north"] + pad_deg, b["east"] + pad_deg
    classes = "|".join(c for c in ROAD_CLASSES if c != "unclassified")   # main roads only: keeps the download small
    q = f'[out:json][timeout:180];way["highway"~"^({classes})$"]({s},{w},{n},{e});out geom;'
    last = None
    for url in OVERPASS:
        for attempt in range(2):
            try:
                _log(f"OpenStreetMap: downloading roads of the study area from {url.split('/')[2]} …")
                r = requests.post(url, data={"data": q}, timeout=200,
                                  headers={"User-Agent": "dhaka-traffic-research/1.0"})
                if r.status_code == 200:
                    data = r.json()
                    _log(f"OpenStreetMap: {len(data.get('elements', []))} road pieces received")
                    return data
                last = f"HTTP {r.status_code}"
            except Exception as ex:
                last = f"{type(ex).__name__}: {str(ex)[:120]}"
            _log(f"OpenStreetMap attempt failed ({last})")
            time.sleep(10)
    raise RuntimeError(f"Overpass failed: {last}")


def _ways_near(osm, lat, lng, radius_m):
    """Only the road pieces whose bounding box comes within radius_m of the point."""
    dlat = radius_m / 111000.0
    dlng = radius_m / (111320.0 * math.cos(math.radians(lat)))
    keep = []
    for w in osm.get("elements", []):
        bb = w.get("_bb")
        if bb is None:
            g = w.get("geometry") or []
            if not g:
                continue
            lats = [p["lat"] for p in g]
            lngs = [p["lon"] for p in g]
            bb = w["_bb"] = (min(lats), max(lats), min(lngs), max(lngs))
        if bb[0] <= lat + dlat and bb[1] >= lat - dlat and bb[2] <= lng + dlng and bb[3] >= lng - dlng:
            keep.append(w)
    return {"elements": keep}


def _build_graph(osm, lat0, lng0):
    nodes, adj = {}, {}
    for w in osm.get("elements", []):
        if w.get("type") != "way" or "geometry" not in w:
            continue
        tags = w.get("tags", {})
        name = tags.get("name:en") or tags.get("name") or tags.get("ref") or ""
        label = " ".join([name, tags.get("name", ""), tags.get("ref", "")]).lower()
        if tags.get("highway") == "motorway" or any(k in label for k in ELEVATED_WORDS):
            continue  # elevated roads do not stop at ground junctions
        weight = ROAD_CLASSES.get(tags.get("highway"), 1)
        ids = w.get("nodes") or [f"{w['id']}_{i}" for i in range(len(w["geometry"]))]
        for nid, g in zip(ids, w["geometry"]):
            nodes[nid] = _xy(g["lat"], g["lon"], lat0, lng0)
        for a, b in zip(ids, ids[1:]):
            for u, v in ((a, b), (b, a)):
                adj.setdefault(u, {})[v] = {"name": name, "weight": weight, "way": w["id"]}
    return nodes, adj


def _snap(nodes, adj, snap_m=300, cluster_m=50):
    """Most important road intersection near the approximate point (0, 0); returns centre and cluster nodes."""
    best, best_val = None, -1e9
    for n, nb in adj.items():
        if len(nb) < 3 and len({e["way"] for e in nb.values()}) < 2:
            continue
        d = math.hypot(*nodes[n])
        if d > snap_m:
            continue
        importance = sum({e["way"]: e["weight"] for e in nb.values()}.values())
        val = importance * 10 - d / 15
        if val > best_val:
            best, best_val = n, val
    if best is None:
        return None, []
    bx, by = nodes[best]
    cluster = [n for n, nb in adj.items()
               if math.hypot(nodes[n][0] - bx, nodes[n][1] - by) <= cluster_m and len(nb) >= 3]
    if best not in cluster:
        cluster.append(best)
    cx = sum(nodes[n][0] for n in cluster) / len(cluster)
    cy = sum(nodes[n][1] for n in cluster) / len(cluster)
    return (cx, cy), cluster


def _walk(nodes, adj, prev, cur, start_poly, max_len):
    """Follows the road outward, always taking the straightest continuation."""
    poly = list(start_poly)
    seen = {prev, cur}
    name = adj[prev][cur]["name"]
    while _length(poly) < max_len:
        here = nodes[cur]
        heading = _bearing(nodes[prev], here)
        best, best_cost = None, 1e9
        for nxt, e in adj.get(cur, {}).items():
            if nxt in seen:
                continue
            turn = _angle_diff(heading, _bearing(here, nodes[nxt]))
            cost = turn - (20 if e["name"] and e["name"] == name else 0)
            if turn <= 45 and cost < best_cost:
                best, best_cost = nxt, cost
        if best is None:
            break
        prev, cur = cur, best
        seen.add(cur)
        poly.append(nodes[cur])
    return poly


def _legs_from_osm(osm, lat0, lng0):
    nodes, adj = _build_graph(osm, lat0, lng0)
    centre, cluster = _snap(nodes, adj)
    if centre is None:
        return None
    cset = set(cluster)
    raw = []
    for u in cluster:
        for v, e in adj[u].items():
            if v in cset:
                continue
            if math.hypot(nodes[v][0] - centre[0], nodes[v][1] - centre[1]) < \
                    math.hypot(nodes[u][0] - centre[0], nodes[u][1] - centre[1]):
                continue  # this edge points back into the junction
            poly = _walk(nodes, adj, u, v, [centre, nodes[u], nodes[v]], config.LEG_LENGTH_M)
            if _length(poly) < 120:
                continue
            raw.append({"poly": poly, "name": e["name"], "weight": e["weight"],
                        "bearing": _bearing(centre, _point_at(poly, min(100, _length(poly))))})
    # one leg per direction: merge parallel carriageways / duplicates
    raw.sort(key=lambda l: (-l["weight"], -_length(l["poly"])))
    legs = []
    for l in raw:
        if all(_angle_diff(l["bearing"], k["bearing"]) > 35 for k in legs):
            legs.append(l)
    legs = legs[:6]
    return {"centre": _ll(*centre, lat0, lng0), "source": "osm",
            "legs": [{"name": l["name"] or "unnamed road", "bearing": round(l["bearing"]),
                      "poly": [_ll(x, y, lat0, lng0) for x, y in l["poly"]]} for l in legs]}


def _radial(lat, lng):
    """Fallback without OpenStreetMap: 8 straight rays from the approximate point."""
    legs = []
    for i, b in enumerate(range(0, 360, 45)):
        x = math.sin(math.radians(b)) * config.LEG_LENGTH_M
        y = math.cos(math.radians(b)) * config.LEG_LENGTH_M
        legs.append({"name": f"{COMPASS8[i]} ray", "bearing": b, "poly": [(lat, lng), _ll(x, y, lat, lng)]})
    return {"centre": (lat, lng), "source": "radial", "legs": legs}


def prepare(force=False):
    """Finds exact junction positions and road directions from OpenStreetMap once and saves them in data/.
    One download for the whole area, a hard time limit, and straight rays as a fallback, so init never hangs."""
    if OSM_FILE.exists() and not force:
        return load()
    DATA.mkdir(exist_ok=True)
    t0 = time.time()
    try:
        osm = _overpass_area()
    except Exception as e:
        _log(f"OpenStreetMap unavailable ({e}); all junctions use straight rays from the approximate point")
        osm = None
    out = []
    for i, (corr, en, bn, lat, lng) in enumerate(JUNCTIONS, 1):
        geo = None
        if osm is not None and time.time() - t0 < PREP_BUDGET_S:
            try:
                geo = _legs_from_osm(_ways_near(osm, lat, lng, config.LEG_LENGTH_M + 400), lat, lng)
            except Exception as e:
                _log(f"{en}: could not read roads ({e})")
        geo = geo or _radial(lat, lng)
        out.append({"id": i, "corridor": corr, "name_en": en, "name_bn": bn, "approx": [lat, lng], **geo})
        _log(f"[{i:02d}/{len(JUNCTIONS)}] {en}: {geo['source']}, {len(geo['legs'])} legs, "
             f"moved {math.hypot(*_xy(geo['centre'][0], geo['centre'][1], lat, lng)):.0f} m")
    _add_neighbours(out)
    OSM_FILE.write_text(json.dumps(out, ensure_ascii=False))
    write_exact_csv(out)
    n_osm = sum(1 for j in out if j["source"] == "osm")
    _log(f"Junctions ready in {time.time() - t0:.0f} s: {n_osm} from OpenStreetMap, {len(out) - n_osm} straight rays")
    return out


def _add_neighbours(js):
    """For each leg: which other junction lies along it, and how far (for spill-back detection)."""
    for j in js:
        lat0, lng0 = j["centre"]
        for leg in j["legs"]:
            poly = [_xy(a, b, lat0, lng0) for a, b in leg["poly"]]
            best = None
            for k in js:
                if k is j:
                    continue
                p = _xy(k["centre"][0], k["centre"][1], lat0, lng0)
                along, off = _project_on(poly, p)
                if off <= 120 and 80 <= along <= _length(poly) and (best is None or along < best[1]):
                    best = (k["name_en"], along)
            leg["toward"] = best[0] if best else ""
            leg["toward_m"] = round(best[1]) if best else None
            leg["label"] = f"{compass8(leg['bearing'])} - {leg['name']}" + (f" (to {best[0]})" if best else "")
            leg["length_m"] = round(_length(poly))


def _project_on(poly, p):
    """Distance along the polyline of the closest point to p, and the offset from it."""
    run, best = 0.0, (0.0, 1e9)
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        dx, dy = x1 - x0, y1 - y0
        seg = math.hypot(dx, dy)
        if seg == 0:
            continue
        t = max(0.0, min(1.0, ((p[0] - x0) * dx + (p[1] - y0) * dy) / seg ** 2))
        off = math.hypot(p[0] - (x0 + t * dx), p[1] - (y0 + t * dy))
        if off < best[1]:
            best = (run + t * seg, off)
        run += seg
    return best


def write_exact_csv(js):
    with EXACT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "corridor", "name_en", "name_bn", "lat", "lng", "approx_lat", "approx_lng", "moved_m",
                    "source", "legs"])
        for j in js:
            moved = math.hypot(*_xy(j["centre"][0], j["centre"][1], *j["approx"]))
            w.writerow([j["id"], j["corridor"], j["name_en"], j["name_bn"], round(j["centre"][0], 6),
                        round(j["centre"][1], 6), j["approx"][0], j["approx"][1], round(moved), j["source"],
                        " | ".join(l["label"] for l in j["legs"])])


def load():
    js = json.loads(OSM_FILE.read_text()) if OSM_FILE.exists() else None
    if js is None:
        js = [{"id": i, "corridor": c, "name_en": en, "name_bn": bn, "approx": [la, ln], **_radial(la, ln)}
              for i, (c, en, bn, la, ln) in enumerate(JUNCTIONS, 1)]
        _add_neighbours(js)
    return js


# ---------------------------------------------------------------- pixel geometry (analysis zoom)
class Geometry:
    """Junction discs and leg sample points in analysis-zoom pixels, plus which tiles each needs."""

    def __init__(self, js):
        self.js = js
        self.items = []
        for j in js:
            cx, cy = config.latlng_to_px(*j["centre"])
            mpp = config.metres_per_px(j["centre"][0])
            legs = []
            for leg in j["legs"]:
                lat0, lng0 = j["centre"]
                poly = [_xy(a, b, lat0, lng0) for a, b in leg["poly"]]
                n = int(_length(poly) // config.SAMPLE_M)
                pts = []
                for k in range(n + 1):
                    d = k * config.SAMPLE_M
                    x0, y0 = _point_at(poly, d)
                    x1, y1 = _point_at(poly, d + 2)
                    px, py = config.latlng_to_px(*_ll(x0, y0, lat0, lng0))
                    qx, qy = config.latlng_to_px(*_ll(x1, y1, lat0, lng0))
                    pts.append((d, px, py, qx - px, qy - py))
                legs.append({**leg, "samples": pts})
            r_px = config.JUNCTION_RADIUS_M / mpp
            reach = (config.LEG_LENGTH_M + 40) / mpp
            x0, x1 = cx - max(reach, r_px), cx + max(reach, r_px)
            y0, y1 = cy - max(reach, r_px), cy + max(reach, r_px)
            tiles = {(tx, ty) for tx in range(int(x0 // config.TILE), int(x1 // config.TILE) + 1)
                     for ty in range(int(y0 // config.TILE), int(y1 // config.TILE) + 1)
                     if 0 <= tx < config.TILES_X and 0 <= ty < config.TILES_Y}
            self.items.append({"j": j, "cx": cx, "cy": cy, "r_px": r_px, "mpp": mpp, "legs": legs,
                               "tiles": tiles, "row": int(cy // config.TILE)})

    def for_shard(self, rows):
        """Junctions whose centre lies in this worker's tile rows."""
        rows = set(rows)
        return [it for it in self.items if it["row"] in rows]


# ---------------------------------------------------------------- measuring
class ClassMap:
    """Per-pixel traffic class from the captured tiles: 0 none, 1 green, 2 orange, 3 red, 4 dark red."""

    def __init__(self):
        self.tiles = {}

    def add(self, tx, ty, masks):
        c = np.zeros(masks[0].shape, dtype=np.uint8)
        for k, m in enumerate(masks, start=1):
            c[m] = k
        self.tiles[(tx, ty)] = c

    def lookup(self, xs, ys):
        xs = np.asarray(xs).round().astype(np.int64)
        ys = np.asarray(ys).round().astype(np.int64)
        out = np.zeros(xs.shape, dtype=np.uint8)
        tx, ty = xs // config.TILE, ys // config.TILE
        for key in set(zip(tx.ravel().tolist(), ty.ravel().tolist())):
            arr = self.tiles.get(key)
            if arr is None:
                continue
            m = (tx == key[0]) & (ty == key[1])
            lx, ly = xs[m] - key[0] * config.TILE, ys[m] - key[1] * config.TILE
            ok = (lx >= 0) & (ly >= 0) & (lx < arr.shape[1]) & (ly < arr.shape[0])
            vals = np.zeros(lx.shape, dtype=np.uint8)
            vals[ok] = arr[ly[ok], lx[ok]]
            out[m] = vals
        return out


def _side_classes(cmap, samples, side):
    """Traffic class on one side of the road at each sample (+1 = right side = traffic toward the junction)."""
    pts = np.array([[s[1], s[2], s[3], s[4]] for s in samples], dtype=float)
    if len(pts) == 0:
        return np.zeros(0, dtype=np.uint8)
    d = np.hypot(pts[:, 2], pts[:, 3])
    d[d == 0] = 1
    ux, uy = pts[:, 2] / d, pts[:, 3] / d
    nx, ny = -uy, ux                     # right-hand normal in image coordinates (y down)
    offs = np.arange(1, config.LANE_SEARCH_PX + 1) * side
    xs = pts[:, 0:1] + nx[:, None] * offs[None, :]
    ys = pts[:, 1:2] + ny[:, None] * offs[None, :]
    cls = cmap.lookup(xs, ys)            # samples x offsets
    out = np.zeros(len(pts), dtype=np.uint8)
    for i in range(len(pts)):
        row = cls[i][cls[i] > 0]
        if row.size:
            out[i] = np.bincount(row, minlength=5)[1:].argmax() + 1
    return out


def _queue(classes, step_m, worst_from):
    """Metres of continuous jam (class >= worst_from) measured outward from the junction."""
    start_gap = int(config.START_GAP_M // step_m)
    gap_allow = int(config.QUEUE_GAP_M // step_m)
    i, n = 0, len(classes)
    while i < n and i <= start_gap and classes[i] < worst_from:
        i += 1
    if i >= n or classes[i] < worst_from:
        return 0.0
    last, gap = i, 0
    while i < n:
        if classes[i] >= worst_from:
            last, gap = i, 0
        elif classes[i] == 0 or classes[i] < worst_from:
            gap += 1
            if gap > gap_allow:
                break
        i += 1
    return round((last + 1) * step_m, 0)


def _score(classes):
    c = classes[classes > 0]
    if c.size < 5:
        return None
    return round(100 * float(np.sum(c - 1)) / (3 * c.size), 1)


def measure(items, cmap, slot, when):
    """Returns (junction_rows, leg_rows) for one slot."""
    jrows, lrows = [], []
    for it in items:
        j = it["j"]
        # disc around the junction
        r = it["r_px"]
        gx, gy = np.meshgrid(np.arange(-r, r + 1, 2), np.arange(-r, r + 1, 2))
        inside = gx ** 2 + gy ** 2 <= r * r
        cls = cmap.lookup(it["cx"] + gx[inside], it["cy"] + gy[inside])
        counts = np.bincount(cls, minlength=5)
        road = counts[1:].sum()
        area_score = round(100 * (counts[2] + 2 * counts[3] + 3 * counts[4]) / (3 * road), 1) if road >= 30 else None
        legs_out, spill = [], []
        for li, leg in enumerate(it["legs"], 1):
            inbound = _side_classes(cmap, leg["samples"], +1)
            outbound = _side_classes(cmap, leg["samples"], -1)
            q_red = _queue(inbound, config.SAMPLE_M, 3)
            q_slow = _queue(inbound, config.SAMPLE_M, 2)
            reaches = bool(leg.get("toward") and leg.get("toward_m") and q_red >= leg["toward_m"] - 100)
            if reaches:
                spill.append(leg["toward"])
            coverage = round(100 * float(np.mean(inbound > 0)), 0) if len(inbound) else 0
            row = {"date": when.date().isoformat(), "time": when.strftime("%H:%M"), "slot": slot,
                   "junction_id": j["id"], "junction": j["name_en"], "leg_id": li, "leg": leg["label"],
                   "bearing": leg["bearing"], "length_m": leg.get("length_m"),
                   "in_score": _score(inbound), "in_queue_red_m": q_red, "in_queue_slow_m": q_slow,
                   "out_score": _score(outbound), "coverage_pct": coverage,
                   "toward": leg.get("toward", ""), "toward_m": leg.get("toward_m"),
                   "reaches_neighbour": "yes" if reaches else ""}
            lrows.append(row)
            legs_out.append(row)
        worst = max(legs_out, key=lambda r: (r["in_queue_red_m"], r["in_score"] or 0), default=None)
        in_scores = [r["in_score"] for r in legs_out if r["in_score"] is not None]
        max_red = max((r["in_queue_red_m"] for r in legs_out), default=0)
        severe = (area_score is not None and area_score >= config.SEVERE_SCORE) or max_red >= config.SEVERE_QUEUE_M
        jrows.append({"date": when.date().isoformat(), "time": when.strftime("%H:%M"), "slot": slot,
                      "junction_id": j["id"], "junction_en": j["name_en"], "junction_bn": j["name_bn"],
                      "corridor": j["corridor"], "lat": round(j["centre"][0], 6), "lng": round(j["centre"][1], 6),
                      "score_area": area_score, "green": int(counts[1]), "orange": int(counts[2]),
                      "red": int(counts[3]), "darkred": int(counts[4]),
                      "mean_in_score": round(float(np.mean(in_scores)), 1) if in_scores else None,
                      "max_queue_red_m": max_red,
                      "max_queue_slow_m": max((r["in_queue_slow_m"] for r in legs_out), default=0),
                      "worst_leg": worst["leg"] if worst else "",
                      "worst_leg_queue_red_m": worst["in_queue_red_m"] if worst else 0,
                      "severe": 1 if severe else 0, "spill_to": "; ".join(spill)})
    return jrows, lrows


JUNCTION_FIELDS = ["date", "time", "slot", "junction_id", "junction_en", "junction_bn", "corridor", "lat", "lng",
                   "score_area", "green", "orange", "red", "darkred", "mean_in_score", "max_queue_red_m",
                   "max_queue_slow_m", "worst_leg", "worst_leg_queue_red_m", "severe", "spill_to"]
LEG_FIELDS = ["date", "time", "slot", "junction_id", "junction", "leg_id", "leg", "bearing", "length_m", "in_score",
              "in_queue_red_m", "in_queue_slow_m", "out_score", "coverage_pct", "toward", "toward_m",
              "reaches_neighbour"]


# ---------------------------------------------------------------- check image
CLASS_RGB = np.array([[235, 235, 235], [46, 158, 79], [240, 160, 48], [220, 59, 47], [123, 31, 34]], dtype=np.uint8)


def check_image(items, cmap, leg_rows, size=260):
    """Grid of small maps: traffic colours, legs (thin black) and the measured red queue (thick blue)."""
    from PIL import Image, ImageDraw, ImageFont
    if not items:
        return None
    cols = 5
    rows_n = math.ceil(len(items) / cols)
    sheet = Image.new("RGB", (cols * size, rows_n * (size + 22)), (255, 255, 255))
    q = {(r["junction_id"], r["leg_id"]): r["in_queue_red_m"] for r in leg_rows}
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
    for k, it in enumerate(items):
        half = (config.LEG_LENGTH_M + 40) / it["mpp"]
        step = 2 * half / size
        gx, gy = np.meshgrid(np.arange(size), np.arange(size))
        cls = cmap.lookup(it["cx"] - half + gx * step, it["cy"] - half + gy * step)
        im = Image.fromarray(CLASS_RGB[cls])
        d = ImageDraw.Draw(im)
        for li, leg in enumerate(it["legs"], 1):
            pts = [((s[1] - it["cx"] + half) / step, (s[2] - it["cy"] + half) / step) for s in leg["samples"]]
            if len(pts) > 1:
                d.line(pts, fill=(0, 0, 0), width=1)
                qm = q.get((it["j"]["id"], li), 0)
                nq = int(qm // config.SAMPLE_M)
                if nq > 1:
                    d.line(pts[:nq + 1], fill=(30, 90, 230), width=4)
        d.ellipse([size / 2 - 4, size / 2 - 4, size / 2 + 4, size / 2 + 4], outline=(0, 0, 0), width=2)
        x, y = (k % cols) * size, (k // cols) * (size + 22)
        sheet.paste(im, (x, y + 22))
        ImageDraw.Draw(sheet).text((x + 4, y + 3), f"{it['j']['id']}. {it['j']['name_en']}"[:34], fill=(0, 0, 0),
                                   font=font)
    return sheet
