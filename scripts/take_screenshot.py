from playwright.sync_api import sync_playwright
import time
import os

def take_screenshots():
    base_url = "file:///C:/Users/HYPER/Desktop/projet-machine-learning-industriel-twinsenseai/frontend/"
    pages_to_capture = {
        "index.html": "screenshot_dashboard.png",
        "machines.html": "screenshot_machines.png",
        "alerts.html": "screenshot_alerts.png",
        "analytics.html": "screenshot_analytics.png"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        
        for file_name, out_name in pages_to_capture.items():
            url = base_url + file_name
            print(f"Capturing {url}...")
            page.goto(url)
            page.wait_for_timeout(2000) # Wait for charts and maps to load
            page.screenshot(path=out_name)
            print(f"Saved {out_name}")
            
        browser.close()

if __name__ == "__main__":
    take_screenshots()
