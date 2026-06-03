import os
import pandas as pd
import requests
from duckduckgo_search import DDGS
import time
import uuid

# Define paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_csv = os.path.join(base_dir, 'data.csv')
images_dir = os.path.join(base_dir, 'backend', 'static', 'images')

os.makedirs(images_dir, exist_ok=True)

df = pd.read_csv(data_csv)

if 'local_image_path' not in df.columns:
    df['local_image_path'] = ''

ddgs = DDGS()
headers = {'User-Agent': 'Mozilla/5.0'}

# Fallback queries if the main one fails to return a good image
def get_fallback_queries(row):
    room_type = str(row.get('room_type', '')).lower()
    gender = str(row.get('gender', '')).lower()
    return [
        f"beautiful {room_type} room hostel {gender} modern",
        f"clean pg accommodation bedroom interior",
        "modern hostel room"
    ]

for index, row in df.iterrows():
    if pd.isna(row['local_image_path']) or not row['local_image_path']:
        pg_name = row['pg_name']
        print(f"[{index+1}/{len(df)}] Searching for {pg_name}...")
        
        queries = [f"{pg_name} PG bangalore bedroom interior"] + get_fallback_queries(row)
        
        success = False
        for query in queries:
            if success:
                break
            try:
                results = ddgs.images(query, max_results=1, safesearch='moderate')
                if results:
                    image_url = results[0]['image']
                    ext = image_url.split('.')[-1].split('?')[0]
                    if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
                        ext = 'jpg'
                    
                    filename = f"pg_{row['pg_id']}_{uuid.uuid4().hex[:6]}.{ext}"
                    filepath = os.path.join(images_dir, filename)
                    
                    resp = requests.get(image_url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        with open(filepath, 'wb') as f:
                            f.write(resp.content)
                        df.at[index, 'local_image_path'] = f"/static/images/{filename}"
                        print(f"  -> Downloaded: {filename}")
                        success = True
                    else:
                        print(f"  -> Failed download (HTTP {resp.status_code}) for url: {image_url}")
                else:
                    print(f"  -> No results for query: {query}")
            except Exception as e:
                print(f"  -> Error for query '{query}': {e}")
                
            time.sleep(1.5) # Be polite to APIs

df.to_csv(data_csv, index=False)
print("Updated data.csv with local image paths.")
