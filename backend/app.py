from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
import os

app = FastAPI(title="Smart Accommodation Recommender API")

# Path to the data file
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data.csv")

# Load and preprocess dataset
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"data.csv not found at {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.strip()

# Map Yes/No to booleans for amenities
bool_cols = ['wifi', 'food_included', 'ac', 'laundry', 'parking', 'student_community_present']
for col in bool_cols:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.lower().map({'yes': True, 'no': False, 'true': True, 'false': False})

# Infer gender dynamically
def infer_gender(pg_id, pg_name):
    name_lower = str(pg_name).lower()
    if any(w in name_lower for w in ["lady", "ladies", "girl", "girls", "women"]):
        return "female"
    elif any(w in name_lower for w in ["boy", "boys", "gent", "gents", "men", "male"]):
        return "male"
    
    # Heuristic for numbered PGs: odd PG number = female, even PG number = male
    try:
        num = int(str(pg_id).replace("PG", "").strip())
        return "male" if num % 2 == 0 else "female"
    except Exception:
        return "unisex"

df['gender'] = df.apply(lambda row: infer_gender(row['pg_id'], row['pg_name']), axis=1)

# Ensure rating columns are numeric
rating_cols = ['locality_safety_rating', 'landlord_responsiveness_rating', 'food_rating', 'overall_student_rating']
for col in rating_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(3.5)

# Ensure numeric cost and distance columns
df['monthly_rent'] = pd.to_numeric(df['monthly_rent'], errors='coerce').fillna(8000)
df['security_deposit'] = pd.to_numeric(df['security_deposit'], errors='coerce').fillna(8000)
df['distance_to_bmsit_km'] = pd.to_numeric(df['distance_to_bmsit_km'], errors='coerce').fillna(5.0)
df['distance_to_bus_stop_km'] = pd.to_numeric(df['distance_to_bus_stop_km'], errors='coerce').fillna(1.0)
df['distance_to_metro_km'] = pd.to_numeric(df['distance_to_metro_km'], errors='coerce').fillna(5.0)

# Global min/max values for WSM normalization
rent_min = float(df['monthly_rent'].min())
rent_max = float(df['monthly_rent'].max())
dist_min = float(df['distance_to_bmsit_km'].min())
dist_max = float(df['distance_to_bmsit_km'].max())
safety_min = float(df['locality_safety_rating'].min())
safety_max = float(df['locality_safety_rating'].max())

class StudentPreferences(BaseModel):
    gender: str
    room_type: str
    budget: int
    wifi: bool = False
    food: bool = False
    ac: bool = False
    laundry: bool = False
    parking: bool = False

class PreferenceWeights(BaseModel):
    cost: float
    distance: float
    safety: float
    quality: float
    amenities: float

class RecommendationRequest(BaseModel):
    preferences: StudentPreferences
    weights: PreferenceWeights
    algorithm: str = "wsm" # "wsm" or "topsis"

@app.get("/api/stats")
def get_stats():
    """Returns analytics and summary metrics of the PGs dataset."""
    total_pgs = len(df)
    avg_rent = float(df['monthly_rent'].mean())
    min_rent = float(df['monthly_rent'].min())
    max_rent = float(df['monthly_rent'].max())
    
    avg_safety = float(df['locality_safety_rating'].mean())
    avg_student_rating = float(df['overall_student_rating'].mean())
    
    # Distance to BMSIT ranges
    avg_distance = float(df['distance_to_bmsit_km'].mean())
    
    # Counts by room type
    room_type_counts = df['room_type'].value_counts().to_dict()
    
    # Counts by locality
    locality_counts = df['locality'].value_counts().to_dict()
    
    # Gender counts
    gender_counts = df['gender'].value_counts().to_dict()
    
    # Average rent by room type
    avg_rent_by_room_type = df.groupby('room_type')['monthly_rent'].mean().to_dict()
    
    return {
        "total_pgs": total_pgs,
        "avg_rent": round(avg_rent, 2),
        "min_rent": min_rent,
        "max_rent": max_rent,
        "avg_safety": round(avg_safety, 2),
        "avg_student_rating": round(avg_student_rating, 2),
        "avg_distance": round(avg_distance, 2),
        "room_type_counts": room_type_counts,
        "locality_counts": locality_counts,
        "gender_counts": gender_counts,
        "avg_rent_by_room_type": {k: round(v, 2) for k, v in avg_rent_by_room_type.items()}
    }

@app.post("/api/recommend")
def recommend_pgs(req: RecommendationRequest):
    pref = req.preferences
    w = req.weights
    alg = req.algorithm.lower()
    
    # Hard Filters
    filtered_df = df.copy()
    
    # 1. Gender Filter
    if pref.gender.lower() == "male":
        filtered_df = filtered_df[filtered_df['gender'].isin(['male', 'unisex'])]
    elif pref.gender.lower() == "female":
        filtered_df = filtered_df[filtered_df['gender'].isin(['female', 'unisex'])]
        
    # 2. Room Type Filter
    if pref.room_type.lower() != "any":
        filtered_df = filtered_df[filtered_df['room_type'].str.lower() == pref.room_type.lower()]
        
    # 3. Budget Filter
    filtered_df = filtered_df[filtered_df['monthly_rent'] <= pref.budget]
    
    m = len(filtered_df)
    if m == 0:
        return []
        
    # Normalize weights so they sum to 1.0
    weight_sum = w.cost + w.distance + w.safety + w.quality + w.amenities
    if weight_sum > 0:
        w_cost = w.cost / weight_sum
        w_dist = w.distance / weight_sum
        w_safety = w.safety / weight_sum
        w_quality = w.quality / weight_sum
        w_amenities = w.amenities / weight_sum
    else:
        w_cost = w_dist = w_safety = w_quality = w_amenities = 0.2
        
    # Selected amenities list
    selected_amenities = []
    if pref.wifi: selected_amenities.append('wifi')
    if pref.ac: selected_amenities.append('ac')
    if pref.food: selected_amenities.append('food_included')
    if pref.laundry: selected_amenities.append('laundry')
    if pref.parking: selected_amenities.append('parking')
    
    # Pre-calculate individual normalized subscores for WSM breakdown (used in card charts)
    subscores = []
    for _, row in filtered_df.iterrows():
        # Cost Score (minimize rent)
        s_cost = 1.0 - (row['monthly_rent'] - rent_min) / (rent_max - rent_min) if rent_max > rent_min else 1.0
        
        # Distance Score (minimize distance)
        s_dist = 1.0 - (row['distance_to_bmsit_km'] - dist_min) / (dist_max - dist_min) if dist_max > dist_min else 1.0
        
        # Safety Score (maximize safety rating)
        s_safety = (row['locality_safety_rating'] - safety_min) / (safety_max - safety_min) if safety_max > safety_min else 1.0
        
        # Quality Score (maximize ratings combination)
        overall_norm = row['overall_student_rating'] / 5.0
        landlord_norm = row['landlord_responsiveness_rating'] / 5.0
        food_norm = row['food_rating'] / 5.0
        s_quality = 0.5 * overall_norm + 0.3 * landlord_norm + 0.2 * food_norm
        
        # Amenities Match Score (maximize matching rate of requested amenities)
        if selected_amenities:
            matches = sum(1 for am in selected_amenities if row[am] == True)
            s_amenity = matches / len(selected_amenities)
        else:
            s_amenity = 1.0
            
        subscores.append({
            "pg_id": row['pg_id'],
            "sub_cost": float(s_cost),
            "sub_dist": float(s_dist),
            "sub_safety": float(s_safety),
            "sub_quality": float(s_quality),
            "sub_amenity": float(s_amenity)
        })
        
    subscores_df = pd.DataFrame(subscores).set_index("pg_id")
    
    # Calculate main ranking scores
    results = []
    
    if alg == "topsis":
        # TOPSIS Decision Matrix: m rows, 5 criteria
        # Criteria: Rent (min), Distance (min), Safety (max), Quality (max), Amenities (max)
        X = np.zeros((m, 5))
        idx_to_pgid = []
        for idx, (_, row) in enumerate(filtered_df.iterrows()):
            pg_id = row['pg_id']
            idx_to_pgid.append(pg_id)
            
            X[idx, 0] = float(row['monthly_rent'])
            X[idx, 1] = float(row['distance_to_bmsit_km'])
            X[idx, 2] = float(row['locality_safety_rating'])
            X[idx, 3] = float(0.5 * row['overall_student_rating'] + 
                              0.3 * row['landlord_responsiveness_rating'] + 
                              0.2 * row['food_rating'])
            X[idx, 4] = float(subscores_df.loc[pg_id, 'sub_amenity'])
            
        # Vector Normalization
        norm_denom = np.sqrt(np.sum(X**2, axis=0))
        norm_denom[norm_denom == 0] = 1e-9 # avoid div by zero
        X_norm = X / norm_denom
        
        # Weighted Normalized Decision Matrix
        w_vec = np.array([w_cost, w_dist, w_safety, w_quality, w_amenities])
        V = X_norm * w_vec
        
        # Determine Ideal positive (best) and negative (worst)
        v_best = np.zeros(5)
        v_worst = np.zeros(5)
        
        # Rent (minimize)
        v_best[0] = np.min(V[:, 0])
        v_worst[0] = np.max(V[:, 0])
        
        # Distance (minimize)
        v_best[1] = np.min(V[:, 1])
        v_worst[1] = np.max(V[:, 1])
        
        # Safety (maximize)
        v_best[2] = np.max(V[:, 2])
        v_worst[2] = np.min(V[:, 2])
        
        # Quality (maximize)
        v_best[3] = np.max(V[:, 3])
        v_worst[3] = np.min(V[:, 3])
        
        # Amenities (maximize)
        v_best[4] = np.max(V[:, 4])
        v_worst[4] = np.min(V[:, 4])
        
        # Distance to positive & negative ideal
        S_best = np.sqrt(np.sum((V - v_best)**2, axis=1))
        S_worst = np.sqrt(np.sum((V - v_worst)**2, axis=1))
        
        # Closeness calculation
        closeness = np.zeros(m)
        for i in range(m):
            denom = S_best[i] + S_worst[i]
            closeness[i] = S_worst[i] / denom if denom > 0 else 0.5
            
        # Compile result list
        for i, (_, row) in enumerate(filtered_df.iterrows()):
            pg_id = row['pg_id']
            record = row.to_dict()
            record['score'] = float(closeness[i])
            record['subscores'] = subscores_df.loc[pg_id].to_dict()
            results.append(record)
            
    else: # Weighted Sum Model (WSM)
        for _, row in filtered_df.iterrows():
            pg_id = row['pg_id']
            sub = subscores_df.loc[pg_id]
            wsm_score = (w_cost * sub['sub_cost'] + 
                         w_dist * sub['sub_dist'] + 
                         w_safety * sub['sub_safety'] + 
                         w_quality * sub['sub_quality'] + 
                         w_amenities * sub['sub_amenity'])
            
            record = row.to_dict()
            record['score'] = float(wsm_score)
            record['subscores'] = sub.to_dict()
            results.append(record)
            
    # Sort results in descending order of score
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    return results

# Serve Frontend static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Mount the static directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))