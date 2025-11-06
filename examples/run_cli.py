import os
from solara.app import app

if __name__ == "__main__":
    location = os.getenv("SW_LOCATION", "Kyoto, Japan")
    month = int(os.getenv("SW_MONTH", "11"))
    res = app.invoke({"location_text": location, "month": month})
    print(res["summary"])
