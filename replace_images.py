
import os
import re

ROOT_DIR = r"d:\sites\coin"
EXCLUDE_DIRS = ["old_pages", "components", "resources"]

# Map old external URL substrings to new local files
REPLACEMENTS = {
    "coins-03.webp": "resources/coins_pile.jpg",
    "top-fon-coin-01.webp": "resources/coins_pile.jpg",
    "gold-002.webp": "resources/gold_stack.jpg",
    "gold-watch-450x350.webp": "resources/gold_watch.jpg",
    "silver-450x350.webp": "resources/silver_pile.png",
    "Jewelry-01.webp": "resources/jewelry.jpg",
    "Collectible-toys.webp": "resources/collectibles.jpg",
    "coin-02-450x350.jpg": "resources/coins_pile.jpg" # Fallback
}

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    
    # Regex to find src="...fairfaxcoin.../filename"
    # match group 1 is the whole url, match group 2 is the filename part if we want
    
    for old_file_part, new_local_path in REPLACEMENTS.items():
        # Pattern: src="[^"]*old_file_part"
        # We need to be careful not to replace something that doesn't match the old domain if it exists (though unlikely)
        # But the USER said "replace all pictures that are pulled from the old site"
        
        # Regex that matches src="http...fairfax.../filename"
        pattern = r'src=["\']https?://fairfaxcoinandbullionexchange\.com[^"\']*/' + re.escape(old_file_part) + r'["\']'
        
        if re.search(pattern, content):
            # Replace with src="new_local_path"
            content = re.sub(pattern, f'src="{new_local_path}"', content)

    if content != original_content:
        print(f"Updating images in {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".html"):
                process_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
