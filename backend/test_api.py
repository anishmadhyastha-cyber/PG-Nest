import sys
import os
from fastapi.testclient import TestClient

# Add current directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

client = TestClient(app)

def test_stats_endpoint():
    """Verify that GET /api/stats returns proper statistical properties."""
    print("Testing GET /api/stats...")
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert "total_pgs" in data
    assert data["total_pgs"] == 70
    assert "avg_rent" in data
    assert "avg_safety" in data
    assert "room_type_counts" in data
    assert "locality_counts" in data
    assert "avg_rent_by_room_type" in data
    
    print("  [PASS] Stats endpoint passed successfully!")
    print(f"  Total PGs: {data['total_pgs']}, Average Rent: {data['avg_rent']}")

def test_recommend_wsm():
    """Verify that WSM algorithm filters and ranks PGs correctly."""
    print("Testing POST /api/recommend (WSM)...")
    payload = {
        "preferences": {
            "gender": "male",
            "room_type": "any",
            "budget": 12000,
            "wifi": True,
            "food": False,
            "ac": False,
            "laundry": False,
            "parking": False
        },
        "weights": {
            "cost": 0.4,       # Prioritize cheap rent
            "distance": 0.1,
            "safety": 0.2,
            "quality": 0.2,
            "amenities": 0.1
        },
        "algorithm": "wsm"
    }
    
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    results = response.json()
    
    # Check that results are not empty
    assert len(results) > 0
    
    # Check that they satisfy hard filters
    for pg in results:
        # Budget filter check
        assert pg["monthly_rent"] <= 12000
        # Gender filter check (male PGs only match male or unisex)
        assert pg["gender"] in ["male", "unisex"]
        
        # Subscores must be present and bounded
        assert "subscores" in pg
        sub = pg["subscores"]
        assert 0.0 <= sub["sub_cost"] <= 1.0
        assert 0.0 <= sub["sub_dist"] <= 1.0
        assert 0.0 <= sub["sub_safety"] <= 1.0
        assert 0.0 <= sub["sub_quality"] <= 1.0
        assert 0.0 <= sub["sub_amenity"] <= 1.0
        assert 0.0 <= pg["score"] <= 1.0

    # Verification: Since cost has a high weight, the top ranks should generally be cheaper PGs
    rents = [pg["monthly_rent"] for pg in results]
    scores = [pg["score"] for pg in results]
    
    # Verify scores are sorted descending
    assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    print(f"  [PASS] WSM endpoint passed! Filtered count: {len(results)}, Top PG: '{results[0]['pg_name']}' (Rent: {results[0]['monthly_rent']}, Score: {results[0]['score']:.4f})")

def test_recommend_topsis():
    """Verify that TOPSIS algorithm filters and ranks PGs correctly."""
    print("Testing POST /api/recommend (TOPSIS)...")
    payload = {
        "preferences": {
            "gender": "female",
            "room_type": "Triple",
            "budget": 10000,
            "wifi": True,
            "food": True,
            "ac": False,
            "laundry": False,
            "parking": False
        },
        "weights": {
            "cost": 0.2,
            "distance": 0.3,   # Prioritize short distance
            "safety": 0.2,
            "quality": 0.1,
            "amenities": 0.2
        },
        "algorithm": "topsis"
    }
    
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    results = response.json()
    
    assert len(results) > 0
    
    # Verify gender, room type, and budget filters
    for pg in results:
        assert pg["gender"] in ["female", "unisex"]
        assert pg["room_type"].lower() == "triple"
        assert pg["monthly_rent"] <= 10000
        assert "score" in pg
        assert 0.0 <= pg["score"] <= 1.0
        
    # Verify scores are sorted descending
    scores = [pg["score"] for pg in results]
    assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    
    print(f"  [PASS] TOPSIS endpoint passed! Filtered count: {len(results)}, Top PG: '{results[0]['pg_name']}' (Dist: {results[0]['distance_to_bmsit_km']}km, Score: {results[0]['score']:.4f})")

if __name__ == "__main__":
    print("Starting FastAPI Integration and Recommender Algorithm Tests...")
    try:
        # Run test cases
        test_stats_endpoint()
        test_recommend_wsm()
        test_recommend_topsis()
        print("\nAll Recommender API integration tests passed successfully!")
    except AssertionError as e:
        print(f"\n[FAIL] Test verification FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Unexpected error running tests: {e}")
        sys.exit(1)
