import os
import glob

replacements = {
    "OCP Jarf Lasfar": "Kennedy Space Center",
    "Jorf Lasfar Slurry Transfer": "Test Facility Alpha",
    "Jorf Lasfar Utility Pumping": "Test Facility Beta",
    "Industrial Water Distribution": "Orbital Assembly",
    "Desalination Pumping Unit": "Launch Complex 39A",
    "Phosphate Slurry Line": "Launch Complex 39B",
    "FL-PUMP-03": "ENG_003",
    "CR-PUMP-07": "ENG_007",
    "FT-MOTOR-02": "ENG_002",
    "DR-MOTOR-11": "ENG_011",
    "Zone 3 · Filtration": "Test Facility Alpha",
    "Zone 1 · Crushing": "Test Facility Beta",
    "Zone 2 · Flotation": "Orbital Assembly",
    "Zone 4 · Drying": "Launch Complex 39A",
    "Zone 3": "Facility A",
    "Zone 1": "Facility B",
    "Zone 2": "Facility C",
    "RLU": "RUL",
    "rlu": "rul",
    "Pression (bar)": "Sensor 2 (LPC Outlet Temp)",
    "Débit (m3/h)": "Sensor 3 (HPC Outlet Temp)",
    "Pression bar": "LPC Outlet Temp",
    "Q (Débit m3/h)": "Sensor 3 (HPC Outlet Temp)",
    "Pd (Pression bar)": "Sensor 2 (LPC Outlet Temp)",
    "Temperature": "Sensor 14",
    "Vibration": "Sensor 15",
    "Pressure": "Sensor 21",
    "Centrifugal Pump": "Turbofan Engine A",
    "Induction Motor": "Turbofan Engine B",
    "Pump": "Engine",
    "Motor": "Engine",
    "Pumps": "Engines",
    "Motors": "Engines",
    "142°C": "142 units",
    "142.5": "642.5",
    "141.8": "641.8",
    "8.4mm/s": "8.4 units",
    "Critical temperature spike": "Critical Sensor 2 spike",
    "Critical Temp Spike (142°C)": "Critical Sensor 2 Spike",
    "Vibration anomaly": "Sensor 15 anomaly",
    "Abnormal Vibration": "Abnormal Sensor 15",
    "15%": "15 cycles",
    "8%": "8 cycles",
    "22%": "22 cycles",
    "31%": "31 cycles",
    "33.098981": "28.5721",
    "-8.602664": "-80.6480",
    "33.099889": "28.5731",
    "-8.596991": "-80.6490",
    "33.101489": "28.5741",
    "-8.600248": "-80.6500",
    "33.101633": "28.6082",
    "-8.605650": "-80.6041",
    "33.098419": "28.6272",
    "-8.607341": "-80.6208",
    "33.100058": "28.5830",
    "-8.600097": "-80.6200",
    "33.098361": "28.5200",
    "-8.610633": "-80.7000",
    "33.101231": "28.6500",
    "-8.594535": "-80.5500",
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
            
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated {file}")
