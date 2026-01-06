
import urllib.request
import re
import os

RESOURCES_DIR = r"d:\sites\coin\resources"

TARGETS = {
    "gold_stack.jpg": "https://commons.wikimedia.org/wiki/File:Gold_bullion_bars.jpg",
    "silver_coin.jpg": "https://commons.wikimedia.org/wiki/File:Morgan_Silver_Dollar_obverse_1921.jpg",
    "gold_watch.jpg": "https://commons.wikimedia.org/wiki/File:Abraham_Lincoln%27s_gold_watch.jpg",
    "jewelry.jpg": "https://commons.wikimedia.org/wiki/File:Napoleon_Diamond_Necklace.jpg",
    "collectibles.jpg": "https://commons.wikimedia.org/wiki/File:Vintage_Toy_Telegraph_Practice_Keys.jpg",
    "coins_pile.jpg": "https://commons.wikimedia.org/wiki/File:Assorted_United_States_coins.jpg"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_original_url(wiki_page_url):
    try:
        req = urllib.request.Request(wiki_page_url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
        # Look for the "Original file" link or the full resolution image
        # Pattern: <a href="https://upload.wikimedia.org/wikipedia/commons/..." class="internal" title="...">Original file</a>
        # Or just find the first upload.wikimedia.org link that contains the filename
        
        filename = wiki_page_url.split("File:")[-1]
        # Decode filename just in case but usually regex handles it
        
        # Regex to find the upload url.
        # It usually looks like: https://upload.wikimedia.org/wikipedia/commons/3/3d/Gold_bullion_bars.jpg
        
        pattern = r'(https://upload\.wikimedia\.org/wikipedia/commons/[a-f0-9]/[a-f0-9]{2}/' + re.escape(filename) + r')'
        match = re.search(pattern, html)
        
        if match:
            return match.group(1)
        
        # Fallback: finding any huge image link?
        # Let's search for "Original file" link specifically
        match = re.search(r'href="(https://upload\.wikimedia\.org/wikipedia/commons/[^"]+)"[^>]*>Original file</a>', html)
        if match:
            return match.group(1)
            
        return None
    except Exception as e:
        print(f"Error fetching page {wiki_page_url}: {e}")
        return None

def download_image(url, filepath):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req) as response:
            with open(filepath, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Downloaded {filepath}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def main():
    if not os.path.exists(RESOURCES_DIR):
        os.makedirs(RESOURCES_DIR)
        
    for local_name, wiki_url in TARGETS.items():
        print(f"Processing {local_name}...")
        img_url = get_original_url(wiki_url)
        if img_url:
            print(f"Found Image URL: {img_url}")
            download_image(img_url, os.path.join(RESOURCES_DIR, local_name))
        else:
            print(f"Could not find image URL for {wiki_url}")

if __name__ == "__main__":
    main()
