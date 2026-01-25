from flask import Flask, render_template
from flask import request, session, redirect
import json
import random
from geometry import *

app = Flask(__name__)
app.secret_key = "geo-game-dev-key"

DIFFICULTY_CONFIG = {
    "easy": {
        "label": "简单",
        "n_cities": 7,
        "time_per_city": 30
    },
    "normal": {
        "label": "普通",
        "n_cities": 12,
        "time_per_city": 30
    },
    "hard": {
        "label": "困难",
        "n_cities": 20,
        "time_per_city": 25
    }
}

# ---------- 工具函数 ----------

def load_cities():
    with open("data/cities.json", "r", encoding="utf-8") as f:
        cities = json.load(f)
    return cities

def calc_score(error):
    """得分计算公式"""
    return min(100, max(0.0, (1000 - error) / 9))


@app.route("/", methods=["GET"])
def index():
    all_cities = load_cities()

    # 默认难度
    difficulty = session.get("difficulty", "easy")
    config = DIFFICULTY_CONFIG[difficulty]

    if "city_order" not in session:
        print("1. Selecting cities for new game...")
        n_cities = config["n_cities"]
        if difficulty == "easy":
            # select all city_hard == 0 (3) + random from city_hard == 1 (4)
            easy_cities = [c for c in all_cities if c["hard"] == 0]
            medium_cities = [c for c in all_cities if c["hard"] == 1]
            selected = easy_cities
            selected += random.sample(medium_cities, n_cities - len(selected))
        elif difficulty == "normal":
            # select random from city hard < 2 (8) + random from city_hard == 2 (4)
            easy_medium_cities = [c for c in all_cities if c["hard"] < 2]
            hard_cities = [c for c in all_cities if c["hard"] == 2]
            selected = random.sample(easy_medium_cities, n_cities - 4)
            selected += random.sample(hard_cities, 4)
        else:  # hard
            # select random from hard cities
            hard_cities = [c for c in all_cities if c["hard"] == 2]
            selected = random.sample(hard_cities, n_cities)
        random.shuffle(selected)
        
        session["city_order"] = [c["name"] for c in selected]

    name_to_city = {c["name"]: c for c in all_cities}
    cities = [name_to_city[name] for name in session["city_order"]]

    total_time = int(len(cities) * config["time_per_city"])

    return render_template(
        "index.html",
        cities=cities,
        difficulty=difficulty,
        difficulty_config=DIFFICULTY_CONFIG,
        total_time=total_time
    )

@app.route("/set_difficulty", methods=["POST"])
def set_difficulty():
    print("2. Setting difficulty...")
    difficulty = request.form.get("difficulty", "easy")

    if difficulty not in DIFFICULTY_CONFIG:
        difficulty = "easy"

    session.clear()
    session["difficulty"] = difficulty

    return redirect("/")

@app.route("/restart")
def restart():
    session.clear()
    return redirect("/")

@app.route("/submit", methods=["POST"])
def submit():
    city_order = session.get("city_order", [])
    all_cities = load_cities()
    name_to_city = {c["name"]: c for c in all_cities}
    cities = [name_to_city[name] for name in city_order]

    results = []
    total_score = 0.0
    n_valid = 0

    for city in cities:
        name = city["name"]
        true_lat = round(city["lat"], 2)
        true_lon = round(city["lon"], 2)

        lat_raw = request.form.get(f"lat_{city['name']}", "").strip()
        lon_raw = request.form.get(f"lon_{city['name']}", "").strip()

        if lat_raw == "" or lon_raw == "":
            user_lat = None
            user_lon = None
        else:
            user_lat = float(lat_raw)
            user_lon = float(lon_raw)   

        error = haversine(user_lat, user_lon, true_lat, true_lon)
        score = calc_score(error)

        total_score += score
        n_valid += 1

        results.append({
            "name": name,
            "user_lat": user_lat,
            "user_lon": user_lon,
            "true_lat": true_lat,
            "true_lon": true_lon,
            "error": error,
            "score": score
        })

    map_data = []
    for r in results:
        if r["user_lat"] is not None:
            dx, dy = km_offset(r["user_lat"], r["user_lon"], 
                               r["true_lat"], r["true_lon"])
            r["dx"] = dx
            r["dy"] = dy
        else:
            r["dx"] = None
            r["dy"] = None
        map_data.append({
            "name": r["name"],
            "true_lat": r["true_lat"],
            "true_lon": r["true_lon"],
            "user_lat": r["user_lat"],
            "user_lon": r["user_lon"]
        })

    if n_valid == 0:
        avg_score = 0.0
    else:
        avg_score = total_score / n_valid
    valid_results = [r for r in results if r["error"] is not None]
    
    max_error_city = max(valid_results, key=lambda x: x["error"]) if valid_results else None
    min_error_city = min(valid_results, key=lambda x: x["error"]) if valid_results else None

    scatter_data = [
        {"x": r["dx"], "y": r["dy"], "city": r["name"]}
        for r in results if r["dx"] is not None
    ]   
    scatter_data_json = json.dumps(scatter_data, ensure_ascii=False)
    map_data_json = json.dumps(map_data, ensure_ascii=False)

    comment = ""
    if avg_score > 90:
        comment = "稳得离谱，你的地理知识可太扎实了。"
    elif avg_score < 60:
        comment = "没关系，地图这种东西就是用来反复看的。"
    else:
        comment = "有准有偏，属于正常人类水平"
        avg_dx = sum(r["dx"] for r in results if r["dx"] is not None) / max(1, len([r for r in results if r["dx"] is not None]))
        if avg_dx > 110: orien = "东"
        elif avg_dx < -110: orien = "西"
        else: orien = ""
        avg_dy = sum(r["dy"] for r in results if r["dy"] is not None) / max(1, len([r for r in results if r["dy"] is not None]))
        if avg_dy > 110: orien += "北"
        elif avg_dy < -110: orien += "南"
        if orien != "":
            comment += f"另外，你的城市定位整体偏{orien}了哦。"
    
    return render_template(
        "results.html",
        results=results,
        avg_score=avg_score,
        max_error_city=max_error_city,
        min_error_city=min_error_city,
        scatter_data_json=scatter_data_json,
        map_data_json=map_data_json,
        comment=comment,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
