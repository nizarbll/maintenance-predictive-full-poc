# TwinSense AI — Predictive Maintenance Platform
## Project Recap & Documentation

**TwinSense AI** is a state-of-the-art predictive maintenance dashboard engineered for aerospace operations at the **Kennedy Space Center**. It provides cycle-by-cycle monitoring, predictive machine learning analytics, and maintenance dispatching to optimize the lifecycle and uptime of NASA turbofan engines.

---

### 🚀 Core Architecture
- **Frontend**: Pure HTML5, Vanilla CSS3 (Custom Design System), and Modular JavaScript.
- **Mapping**: Integrated **Leaflet.js** with Esri Satellite imagery for high-fidelity visualization of launch complexes and test facilities.
- **Data Visualization**: **Chart.js** for mapping multi-dimensional CMAPSS sensor telemetry and RUL (Remaining Useful Life) degradation curves.
- **Branding**: Fully custom **TwinSense AI** design language with premium dark-mode aesthetics, responsive layouts, and fluid micro-animations.

---

### 🛠️ Key Features

#### 1. Facility Map Dashboard (`index.html`)
- **Multi-Mode Visualization**: Toggle between **Live** status, **Heatmap** (fleet stress intensity), and **Satellite** view (Kennedy Space Center layout).
- **Interactive Zones**: 5 specific aerospace zones (Test Facility Alpha, Test Facility Beta, Orbital Assembly, Launch Complex 39A, Launch Complex 39B).
- **Normalized Symbols**: Map markers use industry-standard engineering/aerospace symbols representing turbofan testing rigs.

#### 2. Machinery Overview (`machines.html`)
- **Fleet Management**: Comprehensive list of all active engine units (e.g., ENG_001, ENG_002) in the testing database.
- **Dynamic Filtering**: Sort assets by Facility or Health Status (Healthy, Warning, Critical) based on RUL predictions.
- **Asset Registration**: Modal-based system to register new turbofan engines to the telemetry network on the fly.

#### 3. Engine Details & Telemetry (`machine-details.html`)
- **Deep-Dive Analytics**: Cycle-by-cycle tracking of critical sensor data, such as Sensor 2 (LPC Outlet Temp) and Sensor 3 (HPC Outlet Temp).
- **Predictive KPIs**:
  - **RUL (Remaining Useful Life)**: Hard measurement of remaining operational cycles before imminent engine failure.
  - **Status Indicators**: Algorithmic classification of engine health derived from the MLOps inference pipeline.
- **Maintenance Actions**: Direct "Create Work Order" functionality integrated into the telemetry view to dispatch engineers.

#### 4. Engineer Dispatch (`technicians.html`)
- **Personnel Tracking**: Real-time status of aerospace engineers and technicians (Available, On-Task, Offline).
- **Technician Registration**: Dynamic system to onboard new personnel with auto-generated avatars (DiceBear API).
- **Task Assignment**: Instant link between critical RUL alerts and available technical staff on site.

#### 5. Intelligence & Alerts (`alerts.html`)
- **Centralized Log**: Aggregated view of all active system warnings and threshold breaches (e.g., Sensor anomalies, critical RUL cycles).
- **Direct Navigation**: "View Details" links alerts directly to the specific engine's telemetry dashboard.

---

### 🎨 Design System
- **Colors**: 
  - `var(--ocp-green)`: #77bc1f (Optimal / Healthy)
  - `var(--red)`: #ff4d4d (Critical Failure Risk)
  - `var(--orange)`: #ffa500 (Predictive Warning)
- **Typography**: Optimized for technical legibility using **Syne** (headers) and **DM Sans** (body/data).

---

### 🔄 Recent Transformations
- **Global Rebranding & Domain Shift**: Transitioned the platform from an industrial phosphate pumping station (Jorf Lasfar) to an aerospace engine monitoring platform (Kennedy Space Center).
- **Metric Normalization**: Standardized all assets strictly into **Turbofan Engines** and replaced abstract percentage health metrics with exact **Remaining Useful Life (Cycles)**.
- **UI Polishing**: Implemented persistent sidebar navigation, satellite-default map views, and replaced generic industrial metrics with precise NASA CMAPSS sensor data references.

---
