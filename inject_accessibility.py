import os

def inject_accessibility():
    script_tag = '<script src="accessibility.js"></script>'
    
    # List all html files
    files = [f for f in os.listdir('.') if f.endswith('.html')]
    
    updated_count = 0
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'accessibility.js' in content:
            print(f"Skipping {file_path}, already injected.")
            continue
            
        # Try to find </body> or </html> or just append at the end
        if '</body>' in content:
            new_content = content.replace('</body>', f'    {script_tag}\n</body>')
        elif '</html>' in content:
            new_content = content.replace('</html>', f'    {script_tag}\n</html>')
        else:
            new_content = content + f'\n{script_tag}'
            
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Updated {file_path}")
        updated_count += 1
        
    print(f"\nDone! Injected accessibility.js into {updated_count} files.")

if __name__ == "__main__":
    inject_accessibility()
