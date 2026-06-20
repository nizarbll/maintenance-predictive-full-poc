import os
import glob
import re

replacements = {
    "pctNum + '%'": "pctNum + ' cycles'",
    "RUL (%)": "RUL (Cycles)",
    "85%": "85 cycles",
    "92%": "92 cycles",
    "FL-PUMP-09": "ENG_009",
    "FL-PUMP-01": "ENG_001",
    "CR-PUMP-02": "ENG_002"
}

frontend_dir = r"C:\Users\HYPER\Desktop\projet-machine-learning-industriel-twinsenseai\frontend"

for root, dirs, files in os.walk(frontend_dir):
    for file in files:
        if file.endswith(".html") or file.endswith(".js") or file.endswith(".css") or file.endswith(".md"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
                
            # specific regex replacements for app.js
            if file == "app.js":
                # Let's adjust the chart logic directly
                pass
            
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {file}")
