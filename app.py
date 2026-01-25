from flask import Flask, render_template
from flask import request, session, redirect
import json
import random
from geometry import *

app = Flask(__name__)
app.secret_key = "geo-game-dev-key"

N_CITIES = 15

# ---------- 工具函数 ----------

def load_cities():
    with open("data/cities.json", "r", encoding="utf-8") as f:
        cities = json.load(f)
    return cities

def calc_score(error):
    """得分公式"""
    return min(100, max(0.0, (1000 - error) / 9))


@app.route("/", methods=["GET"])
def index():
    all_cities = load_cities()

    if "city_order" not in session:
        selected = random.sample(all_cities, N_CITIES)
        session["city_order"] = [c["name"] for c in selected]

    # 根据 session 顺序恢复城市对象
    name_to_city = {c["name"]: c for c in all_cities}
    cities = [name_to_city[name] for name in session["city_order"]]

    return render_template(
        "index.html",
        cities=cities,
        lat_range="18°N – 54°N",
        lon_range="73°E – 135°E",
        total_time=len(cities) * 2
    )


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
            map_data.append({
                "name": r["name"],
                "true_lat": r["true_lat"],
                "true_lon": r["true_lon"],
                "user_lat": r["user_lat"],
                "user_lon": r["user_lon"]
            })
        else:
            r["dx"] = None
            r["dy"] = None

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

    if avg_score > 90:
        comment = "优秀！你的中国地理知识非常扎实！"
    elif avg_score < 20:
        comment = "成绩不理想！去看看地图，熟悉一下各大城市的地理位置吧！"
    
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
    app.run(debug=True)
