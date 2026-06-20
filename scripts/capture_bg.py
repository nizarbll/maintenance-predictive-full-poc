import os
from playwright.sync_api import sync_playwright

html_content = """<!doctype html>
<html>
<head>
    <style>body { margin: 0; overflow: hidden; width: 1280px; height: 800px; }</style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vanta@latest/dist/vanta.net.min.js"></script>
</head>
<body>
    <div id="vanta-canvas" style="width:100vw; height:100vh;"></div>
    <script>
        VANTA.NET({
            el: "#vanta-canvas",
            color: 0x0088ff,
            backgroundColor: 0xf5f7fa,
            points: 12.00,
            maxDistance: 22.00,
            spacing: 18.00,
            showDots: true
        });
    </script>
</body>
</html>"""

with open("temp_bg.html", "w", encoding="utf-8") as f:
    f.write(html_content)

abs_path = os.path.abspath("temp_bg.html").replace('\\', '/')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(f"file:///{abs_path}")
    page.wait_for_timeout(3000)
    page.screenshot(path="../presentation/bg.png")
    browser.close()

os.remove("temp_bg.html")
print("Background captured.")
