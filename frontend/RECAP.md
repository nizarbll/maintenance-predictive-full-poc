# TwinSense AI — Predictive Maintenance Platform
## Project Recap & Documentation

**TwinSense AI** is a state-of-the-art industrial dashboard designed for the **Jorf Lasfar** facility. It provides real-time monitoring, predictive analytics, and personnel management to optimize machinery uptime and maintenance workflows.

---

### 🚀 Core Architecture
- **Frontend**: Pure HTML5, Vanilla CSS3 (Custom Design System), and Modular JavaScript.
- **Mapping**: Integrated **Leaflet.js** with Esri Satellite imagery for high-fidelity factory floor visualization.
- **Data Visualization**: **Chart.js** for real-time telemetry and RLU (Remaining Useful Life) tracking.
- **Branding**: Fully custom **TwinSense AI** design language with premium dark-mode aesthetics and fluid micro-animations.

---

### 🛠️ Key Features

#### 1. Factory Map Dashboard (`index.html`)
- **Multi-Mode Visualization**: Toggle between **Live** status, **Heatmap** (stress intensity), and **Satellite** view (factory floor layout).
- **Interactive Zones**: 5 specific Jorf Lasfar zones (Slurry Transfer, Utility Pumping, Water Distribution, Desalination, Slurry Line).
- **Normalized Symbols**: Map markers use industry-standard engineering symbols:
  - **(M)**: Induction/Synchronous Motors.
  - **(Triangle Circle)**: Centrifugal/Slurry Pumps.

#### 2. Machinery Overview (`machines.html`)
- **Fleet Management**: Comprehensive list of all 46+ machines in the facility.
- **Dynamic Filtering**: Sort assets by Zone or Health Status (Healthy, Warning, Critical).
- **Asset Registration**: Modal-based system to add new industrial assets to the database on-the-fly.

#### 3. Machine Details & Telemetry (`machine-details.html`)
- **Deep-Dive Analytics**: Real-time vibration (mm/s) and temperature (°C) telemetry.
- **Predictive KPIs**:
  - **RLU (Remaining Useful Life)**: Percentage of lifespan left before failure.
  - **ETF (Estimated Time to Failure)**: AI-driven breakdown prediction.
- **Maintenance Actions**: Direct "Create Work Order" functionality integrated into the telemetry view.

#### 4. Technician Dispatch (`technicians.html`)
- **Personnel Tracking**: Real-time status of technicians (Available, On-Task, Offline).
- **Technician Registration**: Dynamic system to onboard new personnel with auto-generated avatars (DiceBear API).
- **Task Assignment**: Instant link between critical machine alerts and available technical staff.

#### 5. Intelligence & Alerts (`alerts.html`)
- **Centralized Log**: Aggregated view of all active system warnings.
- **Direct Navigation**: "View Details" links alerts directly to the specific machine's telemetry dashboard.

---

### 🎨 Design System
- **Colors**: 
  - `var(--ocp-green)`: #77bc1f (Industrial Safety)
  - `var(--red)`: #ff4d4d (Critical Failure)
  - `var(--orange)`: #ffa500 (Predictive Warning)
- **Typography**: Optimized for industrial legibility using **Syne** (headers) and **DM Sans** (body/data).

---

### 🔄 Recent Transformations
- **Global Rebranding**: Transitioned from *OCP Predict* to the unified **TwinSense AI** brand identity.
- **Data Normalization**: Standardized all assets strictly into **Pumps** and **Motors** to match the industrial focus of Jorf Lasfar.
- **UI Polishing**: Implemented persistent sidebar navigation, satellite-default map views, and replaced generic emojis with vector engineering symbols.

---
*Developed for the Future of Industrial Intelligence.*
