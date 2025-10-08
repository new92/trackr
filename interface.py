import math
from flask import Flask, jsonify, render_template, request
from api import fetch, static
from deep_translator import GoogleTranslator


app = Flask(__name__)
lang = "en"
resp = fetch()

def translate(data):
    if isinstance(data, dict):
        return {key: translate(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [translate(item) for item in data]
    elif isinstance(data, str):
        return GoogleTranslator(source='auto', target=lang).translate(data)
    else:
        return data

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.asin(math.sqrt(a))

@app.route("/api", methods=["GET"])
def api():
    return jsonify(translate(resp))

@app.route("/api/static", methods=["GET"])
def statapi():
    return jsonify(translate(static()))

@app.route("/api/nearest", methods=["POST"])
def nearest():
    loc = request.json
    lat, lng, lang, stran = loc["lat"], loc["lng"], loc.get("lang", "el"), []
    for s in resp["stations"]:
        t = s.copy()
        t["name"] = GoogleTranslator(source='auto', target=lang).translate(s["name"])
        stran.append(t)
    return jsonify(
        min(
            stran,
            key=lambda s: haversine(lat, lng, s["lat"], s["lng"])
        )
    )

@app.route("/", methods=["GET"])
def index():
    global lang
    lang = request.args.get("lang", "el")
    return render_template(
        "index.html",
        data=api().get_json(),
        static=statapi().get_json(),
        language=lang
    )

if __name__ == '__main__':
    app.run(debug=True)