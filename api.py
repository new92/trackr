import requests, re
from datetime import datetime
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
}

def fetch() -> dict:
    def parsean(announcement: str) -> datetime | None:
        months = {
            "Ιανουαρίου": 1,
            "Φεβρουαρίου": 2,
            "Μαρτίου": 3,
            "Απριλίου": 4,
            "Μαΐου": 5,
            "Ιουνίου": 6,
            "Ιουλίου": 7,
            "Αυγούστου": 8,
            "Σεπτεμβρίου": 9,
            "Οκτωβρίου": 10,
            "Νοεμβρίου": 11,
            "Δεκεμβρίου": 12
        }
        pattern = r"(\d{1,2})\s+([Α-Ωα-ω]+)\s+στις\s+(\d{2})\.(\d{2})"
        match = re.search(pattern, announcement)
        if not match:
            return None
        day, monthname, hour, mint = int(match.group(1)), match.group(2), int(match.group(3)), int(match.group(4))
        if "πρωί" in announcement and hour == 12:
            hour = 0
        elif "απόγευμα" in announcement or "βράδυ" in announcement:
            if hour < 12:
                hour += 12
        elif "μεσημέρι" in announcement:
            hour = 12
        month = months.get(monthname, None)
        if not month:
            return None
        return datetime(datetime.now().year, month, day, hour, mint)
    resp = requests.get("https://www.thessmetro.gr/", headers=headers)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        op = soup.find("div", class_="eventbox-header-operation-name").text.strip()
        andiv = soup.find("div", class_="ticker__item")
        announcement = andiv.text.strip()
        announcement = announcement[announcement.find("Ανακοίνωση:")+11:].replace("\\xa0", "").replace("  ", "").strip()
        anurl = andiv.find("a")
        anurl = anurl["href"] if anurl else ""
        data = {
            "status": "ok",
            "code": resp.status_code,
            "working": "ΝΑΙ" if op == "Κανονική Λειτουργία" else "ΟΧΙ",
            "operation": op,
            "announcement": announcement,
            "announcement_url": anurl
        }
        elevs = []
        for li in soup.find("ul", class_="interactive-map").find_all("li"):
            div = li.find("div", class_="station-status kanoniki btn btn-primary")
            if div is None:
                div = li.find("div", class_="station-status ektos btn btn-primary")    
            elevs.append({"station": div.get("data-bs-stationname"),
                        "working": div.get("data-bs-elevator") == "Οι ανελκυστήρες λειτουργούν κανονικά",
                        "status": div.get("data-bs-elevator")})
        data.update({"elevators": elevs, "elevatorsWorking": 13 - sum(1 for i in range(len(elevs)) if not elevs[i]["working"])})
        stations = []
        coords = [
            (40.6439516, 22.9287502),
            (40.640951, 22.9344741),
            (40.637038, 22.9420217),
            (40.6346834, 22.9464947),
            (40.6308467, 22.9542157),
            (40.6263423, 22.9605221),
            (40.6197492, 22.9630217),
            (40.6157951, 22.9605732),
            (40.6119797, 22.9573395),
            (40.6060329, 22.957921), 
            (40.601075, 22.9585311),
            (40.5952071, 22.9605947),
            (40.5932339, 22.9685282) 
        ]
        statemp = [data["elevators"][i]["station"] for i in range(len(data["elevators"]))]
        date = parsean(data["announcement"])
        now = datetime.now()
        for i in range(len(statemp)):
            tempdata = {"name": statemp[i], "lat": coords[i][0], "lng": coords[i][1]}
            state = statemp[i] in data["announcement"]
            if state:
                if date:
                    if date > now:
                        tempdata.update({"working": state})
                    else:
                        tempdata.update({"working": not state})
                else:
                    tempdata.update({"working": not state})
            else:
                tempdata.update({"working": not state})
            stations.append(tempdata)
        data.update({"stations": stations, "stationsWorking": 13 - sum(1 for i in range(len(stations)) if not stations[i]["working"])})
        return data
    else:
        return {"status": "fail", "code": resp.status_code}
    
def static() -> dict:
    return {
        "station": "Σταθμός",
        "operation": "Κανονική Λειτουργία",
        "oos": "Εκτός Λειτουργίας",
        "true": "ΝΑΙ 🟢",
        "false": "ΟΧΙ 🔴",
        "elevator": "Ανελκυστήρας Σταθμού",
        "announcement": "Ανακοίνωση",
        "nearest": "Πλησιέστερος σταθμός",
        "detect": "Ανίχνευση",
        "error": "Δεν βρέθηκε σταθμός.",
        "opst": "Λειτουργικοί Σταθμοί",
        "opel": "Λειτουργικοί Ανελκυστήρες"
    }