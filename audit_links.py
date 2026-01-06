
import os

ROOT_DIR = r"d:\sites\coin"
EXCLUDE_DIRS = ["old_pages", "components", "resources"]

def audit_structure():
    missing_footer = []
    missing_menu = []
    
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(".html"):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '<footer' not in content:
                    missing_footer.append(file)
                
                if 'id="mobile-menu"' not in content:
                    missing_menu.append(file)

    print("=== Pages Missing Footer ===")
    for f in missing_footer:
        print(f)
        
    print("\n=== Pages Missing Mobile Menu ===")
    for f in missing_menu:
        print(f)

if __name__ == "__main__":
    audit_structure()
