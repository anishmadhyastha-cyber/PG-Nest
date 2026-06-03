import os
import pandas as pd
import shutil
from bing_image_downloader import downloader

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_csv = os.path.join(base_dir, 'data.csv')
images_dir = os.path.join(base_dir, 'backend', 'static', 'images', 'pg-listings')
temp_dir = os.path.join(base_dir, 'temp_images')

os.makedirs(images_dir, exist_ok=True)
os.makedirs(temp_dir, exist_ok=True)

df = pd.read_csv(data_csv)

for index, row in df.iterrows():
    pg_name = row['pg_name']
    query = f"{pg_name} PG accommodation room interior bangalore"
    print(f"Scraping for: {pg_name}")
    try:
        downloader.download(query, limit=1, output_dir=temp_dir, adult_filter_off=False, force_replace=False, timeout=10)
        query_dir = os.path.join(temp_dir, query)
        if os.path.exists(query_dir):
            files = os.listdir(query_dir)
            if files:
                file_ext = os.path.splitext(files[0])[1]
                if not file_ext:
                    file_ext = '.jpg'
                new_filename = f"pg_{row['pg_id']}{file_ext}"
                new_filepath = os.path.join(images_dir, new_filename)
                
                shutil.copy(os.path.join(query_dir, files[0]), new_filepath)
                df.at[index, 'local_image_path'] = f"/static/images/pg-listings/{new_filename}"
                print(f"Saved {new_filename}")
    except Exception as e:
        print(f"Failed for {pg_name}: {e}")

df.to_csv(data_csv, index=False)
shutil.rmtree(temp_dir, ignore_errors=True)
print("Finished scraping 70 images and updated data.csv!")
