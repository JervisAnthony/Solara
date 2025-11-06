from solara.models import POI

def test_poi_default_category():
    poi = POI(name="Test Place")
    assert poi.category == "tourist_attraction"
