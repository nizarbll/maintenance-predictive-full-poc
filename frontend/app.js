// Loader and App Initialization
window.addEventListener('load', () => {
  setTimeout(() => {
    const loader = document.getElementById('loader');
    const app = document.getElementById('app');

    if (loader) loader.classList.add('out');
    if (app) app.classList.add('visible');

    // Initialize specific page logic if elements exist
    if (document.getElementById('map')) {
      initMap();
    }

    if (document.getElementById('rulDoughnut') && document.getElementById('sensorChart')) {
      initCharts();
      animateBars();
    }
  }, 800); // 800ms standard wait, 1500ms originally for map but 800 is faster
});

/* ------------------ Map Logic ------------------ */
// Zone data - UK phosphate mine (Jorf Lasfar)
const zones = [

  { id: 'zone1', name: 'Test Facility Alpha', lat: 28.5721, lng: -80.6480, status: 'healthy', machines: 12, active: 10, warning: 2, critical: 0, rul: 78 },
  { id: 'zone2', name: 'Test Facility Beta', lat: 28.5731  , lng: -80.6490, status: 'warning', machines: 8, active: 5, warning: 2, critical: 1, rul: 45 },
  { id: 'zone3', name: 'Orbital Assembly', lat: 28.5741, lng: -80.6500  , status: 'critical', machines: 10, active: 4, warning: 3, critical: 3, rul: 12 },
  { id: 'zone4', name: 'Launch Complex 39A', lat: 28.6082, lng: -80.6041, status: 'healthy', machines: 10, active: 9, warning: 1, critical: 0, rul: 82 },
  { id: 'zone5', name: 'Launch Complex 39B', lat: 28.6272, lng: -80.6208, status: 'warning', machines: 6, active: 4, warning: 2, critical: 0, rul: 38 }
];

let map;
let markers = {};

function initMap() {
  // Define factory bounds (the area we want to show)
  const factoryBounds = [
    [28.5200, -80.7000], // Southwest
    [28.6500, -80.5500]  // Northeast
  ];

  if (typeof L === 'undefined') return; // Fail gracefully if Leaflet is not loaded

  map = L.map('map', {
    center: [28.5830, -80.6200],
    zoom: 17,
    zoomControl: true,
    minZoom: 15.1,
    maxZoom: 19,
    maxBounds: factoryBounds,
    maxBoundsViscosity: 0.8
  });

  // OpenStreetMap as base (better global coverage)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map);

  // Add satellite overlay layer (Google-like hybrid)
  const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: '© Esri',
    maxZoom: 19,
    opacity: 1
  });

  // Store for toggle
  window.satelliteLayer = satelliteLayer;

  // Add factory boundary rectangle
  const factoryBoundary = L.rectangle(factoryBounds, {
    color: '#00875A',
    weight: 0,
    fillColor: '#00875A',
    fillOpacity: 0.08,
    dashArray: '10, 10'
  }).addTo(map);

  // Fit map to factory bounds
  map.fitBounds(factoryBounds, { padding: [50, 50] });

  addZoneMarkers();
  setTimeout(() => window.setMapMode('satellite'), 100);
}

function addZoneMarkers() {
  zones.forEach(zone => {
    const statusClass = `zone-marker-${zone.status}`;
    const color = zone.status === 'healthy' ? 'var(--ocp-green)' : zone.status === 'warning' ? 'var(--orange)' : 'var(--red)';
    
    // Normalized symbols
    const motorSvg = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" font-size="12" font-family="sans-serif" font-weight="bold" fill="currentColor" stroke="none">M</text></svg>`;
    const pumpSvg = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="7,16 17,16 12,7" fill="currentColor" stroke="none"/></svg>`;
    
    // Assign pump or motor based on zone name
    const iconHtml = zone.name.toLowerCase().includes('pump') ? pumpSvg : motorSvg;

    const markerHtml = `
      <div class="zone-marker ${statusClass}">
        <div class="zone-marker-inner" style="color:${color}; display:flex; align-items:center; justify-content:center;">
          ${iconHtml}
        </div>
      </div>
    `;

    const icon = L.divIcon({
      html: markerHtml,
      className: 'zone-marker',
      iconSize: [52, 52],
      iconAnchor: [26, 26]
    });

    const marker = L.marker([zone.lat, zone.lng], { icon }).addTo(map);

    const popupContent = `
      <div class="zone-popup-content">
        <div class="zone-popup-title">${zone.name}</div>
        <div class="zone-popup-sub">${zone.machines} machines · ${zone.active} active</div>
        <div class="zone-popup-stats">
          <div class="zone-popup-stat">
            <div class="zone-popup-stat-val" style="color:var(--ocp-green)">${zone.active}</div>
            <div class="zone-popup-stat-lbl">Healthy</div>
          </div>
          <div class="zone-popup-stat">
            <div class="zone-popup-stat-val" style="color:var(--orange)">${zone.warning}</div>
            <div class="zone-popup-stat-lbl">Warning</div>
          </div>
          <div class="zone-popup-stat">
            <div class="zone-popup-stat-val" style="color:var(--red)">${zone.critical}</div>
            <div class="zone-popup-stat-lbl">Critical</div>
          </div>
        </div>
        <a href="machines.html" class="zone-popup-btn">View Machines →</a>
      </div>
    `;

    marker.bindPopup(popupContent, { className: 'zone-popup', maxWidth: 280 });
    markers[zone.id] = marker;
  });
}

window.setMapMode = function (mode) {
  if (!map) return;
  document.querySelectorAll('.map-ctrl-btn').forEach(btn => btn.classList.remove('active'));
  if (typeof event !== 'undefined' && event && event.target) {
    event.target.classList.add('active');
  } else {
    const btn = document.querySelector(`.map-ctrl-btn[onclick*="'${mode}'"]`);
    if (btn) btn.classList.add('active');
  }

  if (mode === 'heatmap') {
    // Show heatmap overlay
    if (!window.heatOverlay && typeof L.heatLayer === 'function') {
      const heatData = [];
      zones.forEach(zone => {
        for (let i = 0; i < zone.machines; i++) {
          const offset = (Math.random() - 0.5) * 0.003;
          const intensity = zone.status === 'critical' ? 1 : zone.status === 'warning' ? 0.6 : 0.3;
          heatData.push([zone.lat + offset, zone.lng + offset, intensity]);
        }
      });
      window.heatOverlay = L.heatLayer(heatData, {
        radius: 30,
        blur: 20,
        maxZoom: 17,
        gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' }
      });
    }
    if (window.heatOverlay) window.heatOverlay.addTo(map);
  } else {
    if (window.heatOverlay) map.removeLayer(window.heatOverlay);
  }

  if (mode === 'satellite') {
    // Show satellite with higher opacity
    if (window.satelliteLayer) {
      map.eachLayer(l => { if (l._url && l._url.includes('openstreetmap')) l.setOpacity(0.3); });
      window.satelliteLayer.addTo(map);
      window.satelliteLayer.setOpacity(0.85);
    }
  } else if (mode === 'live') {
    // Live mode - clean view
    map.eachLayer(l => { if (l._url && l._url.includes('openstreetmap')) l.setOpacity(1); });
    if (window.satelliteLayer) map.removeLayer(window.satelliteLayer);
  }
};

/* ------------------ Machine Details Charts ------------------ */
function animateBars() {
  document.querySelectorAll('.pred-bar-fill').forEach(bar => {
    bar.style.width = bar.getAttribute('data-width');
  });
}

function initCharts() {
  if (typeof Chart === 'undefined') return;

  Chart.defaults.font.family = "'JetBrains Mono', monospace";
  Chart.defaults.color = "#8E97A3";

  // RUL Doughnut
  const rulCanvas = document.getElementById('rulDoughnut');
  if (rulCanvas) {
    const ctxRlu = rulCanvas.getContext('2d');
    new Chart(ctxRlu, {
      type: 'doughnut',
      data: {
        labels: ['Consumed Life', 'Remaining Life'],
        datasets: [{
          data: [92, 8],
          backgroundColor: ['#F0F3F5', '#750d0d'],
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        cutout: '75%',
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        animation: { animateScale: true, animateRotate: true, duration: 1500 }
      }
    });
  }

  // Sensor Line Chart
  const sensorCanvas = document.getElementById('sensorChart');
  if (sensorCanvas) {
    const ctxSensor = sensorCanvas.getContext('2d');

    // Generate mock data (daily cycles to simulate RUL degradation)
    const labels = Array.from({ length: 30 }, (_, i) => `Cycle ${100 + i}`);
    const s2Data = labels.map((_, i) => 641.5 + (i * 0.05) + Math.random() * 0.5);
    const s3Data = labels.map((_, i) => 1585 - (i * 1.5) - Math.random() * 5);

    new Chart(ctxSensor, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Sensor 2 (LPC Outlet Temp)',
            data: s2Data,
            borderColor: '#750d0d',
            backgroundColor: 'rgba(117, 13, 13, 0.05)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4,
            yAxisID: 'y'
          },
          {
            label: 'Sensor 3 (HPC Outlet Temp)',
            data: s3Data,
            borderColor: '#8d3a03',
            borderWidth: 2,
            pointRadius: 0,
            borderDash: [5, 5],
            tension: 0.4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 6, font: { size: 11, family: "'DM Sans', sans-serif" } } }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            type: 'linear', display: true, position: 'left',
            grid: { color: 'rgba(0,0,0,0.04)' },
            title: { display: true, text: 'LPC Temp (°R)', font: { size: 10 } }
          },
          y1: {
            type: 'linear', display: true, position: 'right',
            grid: { display: false },
            title: { display: true, text: 'HPC Temp (°R)', font: { size: 10 } }
          }
        }
      }
    });
  }
}


// Dropdown toggle logic
window.toggleDropdown = function (id) {
  document.querySelectorAll('.dropdown-menu').forEach(menu => {
    if (menu.id !== id) menu.classList.remove('show');
  });
  const menu = document.getElementById(id);
  if (menu) menu.classList.toggle('show');
};

document.addEventListener('click', (e) => {
  if (!e.target.closest('.dropdown-wrapper')) {
    document.querySelectorAll('.dropdown-menu').forEach(menu => {
      menu.classList.remove('show');
    });
  }
});

// Simulation of file downloads
window.downloadFile = function (type, filename) {
  let content = '';
  let mimeType = 'text/plain';

  if (type === 'csv') {
    content = 'Timestamp,Machine_ID,Sensor 14,Sensor 15,Sensor 21\n' +
      new Date().toISOString() + ',ENG_003,642.5,8.2,12.1\n' +
      new Date(Date.now() - 1000).toISOString() + ',ENG_003,641.8,7.9,11.9';
    mimeType = 'text/csv';
  } else if (type === 'pdf') {
    content = '%PDF-1.4\n%... [Simulated OCP Machine Report for ' + filename + '] ...';
    mimeType = 'application/pdf';
  } else if (type === 'xlsx') {
    content = '[Simulated Excel Data for Maintenance History]';
    mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
  }

  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);

  console.log('Downloaded: ' + filename);
};

// Machine list filtering logic
window.addEventListener('load', () => {
  const filterSelects = document.querySelectorAll('.filter-select');
  if (filterSelects.length >= 2) {
    const zoneSelect = filterSelects[0];
    const statusSelect = filterSelects[1];
    const tableBody = document.querySelector('tbody');

    if (tableBody) {
      const rows = tableBody.querySelectorAll('tr');

      function applyFilters() {
        const zoneFilter = zoneSelect.value.toLowerCase().trim();
        const statusFilter = statusSelect.value.toLowerCase().trim();

        rows.forEach(row => {
          if (row.cells.length >= 3) {
            const rowZone = row.cells[1].textContent.toLowerCase();
            const rowStatus = row.cells[2].textContent.toLowerCase();

            let zoneMatch = true;
            if (zoneFilter !== 'all zones' && zoneFilter !== '') {
               const zonePrefix = zoneFilter.split('·')[0].trim();
               zoneMatch = rowZone.includes(zonePrefix);
            }

            let statusMatch = true;
            if (statusFilter !== 'all statuses' && statusFilter !== '') {
               statusMatch = rowStatus.includes(statusFilter);
            }

            if (zoneMatch && statusMatch) {
              row.style.display = '';
            } else {
              row.style.display = 'none';
            }
          }
        });
      }

      zoneSelect.addEventListener('change', applyFilters);
      statusSelect.addEventListener('change', applyFilters);
    }
  }
});


/* ------------------ Register Machine Logic ------------------ */
window.registerMachine = function() {
  openRegisterMachineModal();
};

function getRegisterMachineModalEls() {
  return {
    overlay: document.getElementById('registerMachineModal'),
    form: document.getElementById('registerMachineForm'),
    id: document.getElementById('rm_id'),
    type: document.getElementById('rm_type'),
    zone: document.getElementById('rm_zone'),
    status: document.getElementById('rm_status'),
    rul: document.getElementById('rm_rul'),
    last: document.getElementById('rm_last')
  };
}

window.openRegisterMachineModal = function() {
  const { overlay, form, id } = getRegisterMachineModalEls();
  if (!overlay || !form) return;

  overlay.classList.add('show');
  // Reset only if the user previously submitted/cancelled
  form.reset();
  if (id) id.focus();
};

window.closeRegisterMachineModal = function() {
  const { overlay } = getRegisterMachineModalEls();
  if (!overlay) return;
  overlay.classList.remove('show');
};

function addMachineRow({ machineId, machineType, zone, status, rulPct, lastInspected }) {
  const tbody = document.querySelector('.machines-container table tbody');
  if (!tbody) return;

  const pctNum = Math.max(0, Math.min(100, Number(rulPct)));
  const badgeClass =
    String(status).toLowerCase().includes('crit') ? 'status-critical' :
    String(status).toLowerCase().includes('warn') ? 'status-warning' :
    'status-healthy';
  const color =
    badgeClass === 'status-critical' ? 'var(--red)' :
    badgeClass === 'status-warning' ? 'var(--orange)' :
    'var(--ocp-green)';

  const tr = document.createElement('tr');
  tr.setAttribute('onclick', "window.location.href='machine-details.html'");
  tr.innerHTML = `
    <td>
      <div class="machine-id">
        <div class="machine-icon">⚙️</div>
        <div>
          <div class="machine-name">${machineId}</div>
          <div class="machine-type">${machineType || 'Machine'}</div>
        </div>
      </div>
    </td>
    <td>${zone}</td>
    <td><span class="status-badge ${badgeClass}">${status}</span></td>
    <td>
      <div class="rul-cell">
        <div class="rul-bar-wrap"><div class="rul-bar-fill" style="width:${pctNum}%;background:${color}"></div></div>
        <span class="rul-pct" style="color:${color}">${isNaN(pctNum) ? '' : pctNum + ' cycles'}</span>
      </div>
    </td>
    <td>${lastInspected || ''}</td>
    <td><button class="action-btn">View Dashboard</button></td>
  `;

  const emptyRow = tbody.querySelector('tr[data-empty-state="1"]');
  if (emptyRow) tbody.insertBefore(tr, emptyRow);
  else tbody.appendChild(tr);

  if (typeof window.filterMachines === 'function') window.filterMachines();
}

document.addEventListener('DOMContentLoaded', () => {
  const { overlay, form } = getRegisterMachineModalEls();
  if (!overlay || !form) return;

  // Close when clicking backdrop
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) window.closeRegisterMachineModal();
  });

  // Close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') window.closeRegisterMachineModal();
  });

  // Handle submit
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const els = getRegisterMachineModalEls();
    const machineId = (els.id?.value || '').trim();
    const zone = (els.zone?.value || '').trim();
    if (!machineId || !zone) return;

    addMachineRow({
      machineId,
      machineType: (els.type?.value || '').trim(),
      zone,
      status: els.status?.value || 'Healthy',
      rulPct: els.rul?.value ?? 100,
      lastInspected: (els.last?.value || '').trim()
    });

    window.closeRegisterMachineModal();
  });
});



/* ------------------ Register Technician Logic ------------------ */
function getRegisterTechModalEls() {
  return {
    overlay: document.getElementById('registerTechModal'),
    form: document.getElementById('registerTechForm'),
    name: document.getElementById('rt_name'),
    role: document.getElementById('rt_role'),
    status: document.getElementById('rt_status'),
    location: document.getElementById('rt_location'),
    shift: document.getElementById('rt_shift')
  };
}

window.openRegisterTechModal = function() {
  const { overlay, form, name } = getRegisterTechModalEls();
  if (!overlay || !form) return;
  overlay.classList.add('show');
  form.reset();
  if (name) name.focus();
};

window.closeRegisterTechModal = function() {
  const { overlay } = getRegisterTechModalEls();
  if (!overlay) return;
  overlay.classList.remove('show');
};

function addTechCard({ name, role, status, location, shift }) {
  const techGrid = document.querySelector('.tech-grid');
  if (!techGrid) return;

  const statusLower = status.toLowerCase();
  let statusClass = 'status-available';
  if (statusLower.includes('task') || statusLower.includes('busy')) {
      statusClass = 'status-busy';
  } else if (statusLower.includes('offline')) {
      statusClass = 'status-offline';
  }

  const avatarUrl = `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(name)}`;

  const card = document.createElement('div');
  card.className = 'tech-card';
  card.innerHTML = `
    <div class="status-dot ${statusClass}">${status}</div>
    <div class="tech-header">
      <div class="tech-avatar" style="background-image:url('${avatarUrl}')"></div>
      <div class="tech-info">
        <div class="tech-name">${name}</div>
        <div class="tech-role">${role}</div>
      </div>
    </div>
    <div class="tech-details">
      <div class="tech-detail-item">
        <svg class="tech-detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
        ${location || 'Unassigned'}
      </div>
      <div class="tech-detail-item">
        <svg class="tech-detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        ${shift || 'Standard Shift'}
      </div>
    </div>
    <div class="tech-actions">
      <button class="tech-btn tech-btn-primary" ${statusClass === 'status-busy' ? 'style="opacity:0.6;cursor:not-allowed"' : "onclick=\"window.location.href='machine-details.html'\""}>Assign Task</button>
      <button class="tech-btn tech-btn-outline">Profile</button>
    </div>
  `;

  // Insert at the beginning of the grid
  techGrid.insertBefore(card, techGrid.firstChild);
}

document.addEventListener('DOMContentLoaded', () => {
  const { overlay, form } = getRegisterTechModalEls();
  if (overlay && form) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) window.closeRegisterTechModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('show')) {
        window.closeRegisterTechModal();
      }
    });

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const els = getRegisterTechModalEls();
      const name = (els.name?.value || '').trim();
      const role = (els.role?.value || '').trim();
      if (!name) return;

      addTechCard({
        name,
        role,
        status: els.status?.value || 'Available',
        location: (els.location?.value || '').trim(),
        shift: (els.shift?.value || '').trim()
      });

      window.closeRegisterTechModal();
    });
  }
});

/* ------------------ Work Order Modal Logic ------------------ */
window.openWorkOrderModal = function(reset = false) {
  const modal = document.getElementById('workOrderModal');
  if (modal) {
    modal.classList.add('show');
    if (reset) {
      const form = document.getElementById('workOrderForm');
      if (form) form.reset();
      
      const fields = document.getElementById('workOrderFields');
      const success = document.getElementById('workOrderSuccess');
      const actionsCreate = document.getElementById('workOrderActionsCreate');
      const actionsSuccess = document.getElementById('workOrderActionsSuccess');
      
      if (fields) fields.style.display = 'grid';
      if (success) success.style.display = 'none';
      if (actionsCreate) actionsCreate.style.display = 'flex';
      if (actionsSuccess) actionsSuccess.style.display = 'none';
    }
    
    // Autofill machine details if we are on the machine details page
    const machineIdInput = document.getElementById('wo_machine');
    const machineZoneInput = document.getElementById('wo_zone');
    if (machineIdInput && !machineIdInput.value) {
      machineIdInput.value = 'ENG_003';
    }
    if (machineZoneInput && !machineZoneInput.value) {
      machineZoneInput.value = 'Facility A (Filtration)';
    }
  }
};

window.closeWorkOrderModal = function() {
  const modal = document.getElementById('workOrderModal');
  if (modal) modal.classList.remove('show');
};

document.addEventListener('DOMContentLoaded', () => {
  const woForm = document.getElementById('workOrderForm');
  if (woForm) {
    woForm.addEventListener('submit', (e) => {
      e.preventDefault();
      
      const fields = document.getElementById('workOrderFields');
      const success = document.getElementById('workOrderSuccess');
      const actionsCreate = document.getElementById('workOrderActionsCreate');
      const actionsSuccess = document.getElementById('workOrderActionsSuccess');
      
      if (fields) fields.style.display = 'none';
      if (success) success.style.display = 'block';
      if (actionsCreate) actionsCreate.style.display = 'none';
      if (actionsSuccess) actionsSuccess.style.display = 'flex';
      
      const machine = document.getElementById('wo_machine').value;
      const type = document.getElementById('wo_severity').value;
      const successId = document.getElementById('workOrderSuccessId');
      const successMeta = document.getElementById('workOrderSuccessMeta');
      
      if (successId) successId.innerText = 'WO-' + Math.floor(Math.random() * 100000);
      if (successMeta) successMeta.innerText = `${machine} · ${type}`;
    });
  }
});
