from solara.nodes.scoring import norm_popularity

def test_norm_popularity_range():
    val = norm_popularity(4.5, 1000)
    assert 0 <= val <= 1
