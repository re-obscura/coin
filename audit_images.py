
import os
import re
from collections import defaultdict

ROOT_DIR = r"d:\sites\coin"
EXCLUDE_DIRS = ["old_pages", "components", "resources"]
OLD_DOMAIN_REGEX = r'src=["\'](https?://fairfaxcoinandbullionexchange\.com[^"\']+)["\']'

def audit_site():
    files_missing_images = []
    external_images = defaultdict(list)
    
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count images (excluding placeholders if possible, but let's just count tags)
                img_count = len(re.findall(r'<img\s', content))
                if img_count < 2:
                    files_missing_images.append((file, img_count))
                
                # Find external images
                matches = re.finditer(OLD_DOMAIN_REGEX, content)
                for m in matches:
                    external_images[file].append(m.group(1))

    print("=== Pages with < 2 Images ===")
    for f, count in files_missing_images:
        print(f"{f}: {count}")
    
    print("\n=== External Images to Replace ===")
    for f, urls in external_images.items():
        print(f"\nFile: {f}")
        for url in urls:
            print(f"  - {url}")

if __name__ == "__main__":
    audit_site()
