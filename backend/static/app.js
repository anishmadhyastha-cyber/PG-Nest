// Application Javascript for PGNest Recommender System

document.addEventListener("DOMContentLoaded", () => {
    // Icons initialization
    lucide.createIcons();

    // Dark Room Feature Toggle
    const btnDarkRoom = document.getElementById('btn-dark-room');
    const applyDarkMode = (enabled) => {
        document.body.classList.toggle('dark-mode', enabled);
        // Swap icon: moon in light mode, sun in dark mode
        const moonIcon = btnDarkRoom.querySelector('.icon-moon');
        const sunIcon  = btnDarkRoom.querySelector('.icon-sun');
        if (moonIcon) moonIcon.style.display = enabled ? 'none'   : '';
        if (sunIcon)  sunIcon.style.display  = enabled ? ''       : 'none';
    };
    if (btnDarkRoom) {
        // Restore saved preference
        const saved = localStorage.getItem('dark-room') === 'enabled';
        applyDarkMode(saved);
        btnDarkRoom.addEventListener('click', () => {
            const isDark = document.body.classList.contains('dark-mode');
            applyDarkMode(!isDark);
            localStorage.setItem('dark-room', !isDark ? 'enabled' : 'disabled');
        });
    }


    // DOM Elements - Wizard Onboarding
    const wizardOverlay = document.getElementById("wizard-overlay");
    const wizardTitle = document.getElementById("wizard-title");
    const closeWizardBtn = document.getElementById("btn-close-wizard");
    const btnWizardBack = document.getElementById("btn-wizard-back");
    const btnWizardNext = document.getElementById("btn-wizard-next");
    const btnStartMatching = document.getElementById("btn-start-matching");
    
    // Wizard step containers
    const stepSection1 = document.getElementById("step-section-1");
    const stepSection2 = document.getElementById("step-section-2");
    const stepSection3 = document.getElementById("step-section-3");
    const progressSteps = document.querySelectorAll(".progress-step");
    
    // Wizard Input Fields
    const budgetSlider = document.getElementById("pref-budget");
    const budgetValueLabel = document.querySelector(".budget-value");
    
    // Ratings elements
    const ratings = {
        cost: document.getElementById("rate-cost"),
        distance: document.getElementById("rate-distance"),
        safety: document.getElementById("rate-safety"),
        quality: document.getElementById("rate-quality"),
        amenities: document.getElementById("rate-amenities")
    };
    
    const ratingLabels = {
        cost: document.getElementById("rate-cost-val"),
        distance: document.getElementById("rate-distance-val"),
        safety: document.getElementById("rate-safety-val"),
        quality: document.getElementById("rate-quality-val"),
        amenities: document.getElementById("rate-amenities-val")
    };

    // Results panel controls
    const recommenderSection = document.getElementById("recommender");
    const listingsGrid = document.getElementById("listings-grid");
    const resultsCountLabel = document.getElementById("results-count");
    const btnEditPriorities = document.getElementById("btn-edit-priorities");
    const algMiniTabs = document.querySelectorAll(".alg-mini-tab");

    // Dynamic Summary Banner Elements
    const summaryGender = document.getElementById("summary-gender");
    const summaryRoom = document.getElementById("summary-room");
    const summaryBudget = document.getElementById("summary-budget");
    const summaryPrioritiesList = document.getElementById("summary-priorities-list");
    
    // Navigation & Analytics Panel
    const navLinks = document.querySelectorAll(".nav-link");
    const analyticsSection = document.getElementById("analytics");
    const closeAnalyticsBtn = document.getElementById("close-analytics");
    
    // Compare Drawer
    const compareDrawer = document.getElementById("compare-drawer");
    const compareCountLabel = document.getElementById("compare-count");
    const compareThumbnails = document.getElementById("compare-thumbnails");
    const clearCompareBtn = document.getElementById("btn-clear-compare");
    const compareNowBtn = document.getElementById("btn-compare-now");
    const closeDrawerBtn = document.getElementById("btn-close-drawer");
    
    // Modals
    const compareModal = document.getElementById("compare-modal");
    const detailsModal = document.getElementById("details-modal");
    const closeModalBtns = document.querySelectorAll(".btn-close-modal");
    const compareTableHead = document.getElementById("compare-table-head");
    const compareTableBody = document.getElementById("compare-table-body");
    const modalDetailsContent = document.getElementById("modal-details-content");
    const modalPgName = document.getElementById("modal-pg-name");

    // Chart variables
    let rentRoomTypeChart = null;
    let rentDistanceChart = null;

    // GLOBAL APP STATE (Stores constraints and ratings to prevent data loss)
    const globalState = {
        gender: "male",
        room_type: "any",
        budget: 12000,
        priorities: {
            cost: 5,
            distance: 5,
            safety: 5,
            quality: 5,
            amenities: 5
        },
        amenities: {
            wifi: false,
            ac: false,
            food: false,
            laundry: false,
            parking: false
        },
        algorithm: "wsm"
    };

    let currentWizardStep = 1;
    let loadedAccommodations = [];
    let selectedForCompare = []; 
    let marketStats = null;

    // Initialize
    initWizardListeners();
    fetchStats();
    loadRecommendations();

    // 1. Hero start button
    if (btnStartMatching) {
        btnStartMatching.addEventListener("click", () => {
            openWizardModal(false); // First onboarding: cannot close without submitting
        });
    }

    // 2. Budget slider labeling
    budgetSlider.addEventListener("input", (e) => {
        const val = parseInt(e.target.value);
        budgetValueLabel.textContent = `₹${val.toLocaleString('en-IN')} max`;
    });

    // 3. 1 to 10 Ratings Labels
    Object.keys(ratings).forEach(key => {
        ratings[key].addEventListener("input", (e) => {
            ratingLabels[key].textContent = `${e.target.value} / 10`;
        });
    });

    // 4. Onboarding Step Navigation Wizard
    function initWizardListeners() {
        btnWizardNext.addEventListener("click", () => {
            if (currentWizardStep === 1) {
                // Move to priorities
                goToStep(2);
            } else if (currentWizardStep === 2) {
                // Move to amenities
                goToStep(3);
            } else if (currentWizardStep === 3) {
                // Submit Form!
                saveWizardState();
                closeWizardModal();
                showView("recommender");
                loadRecommendations();
            }
        });

        btnWizardBack.addEventListener("click", () => {
            if (currentWizardStep > 1) {
                goToStep(currentWizardStep - 1);
            }
        });

        closeWizardBtn.addEventListener("click", () => {
            closeWizardModal();
        });
    }

    function goToStep(step) {
        currentWizardStep = step;
        
        // Hide all steps
        stepSection1.classList.add("hidden");
        stepSection2.classList.add("hidden");
        stepSection3.classList.add("hidden");
        
        // Show current step
        if (step === 1) {
            stepSection1.classList.remove("hidden");
            btnWizardBack.classList.add("invisible");
            btnWizardNext.innerHTML = `Next <i data-lucide="chevron-right"></i>`;
        } else if (step === 2) {
            stepSection2.classList.remove("hidden");
            btnWizardBack.classList.remove("invisible");
            btnWizardNext.innerHTML = `Next <i data-lucide="chevron-right"></i>`;
        } else if (step === 3) {
            stepSection3.classList.remove("hidden");
            btnWizardBack.classList.remove("invisible");
            btnWizardNext.innerHTML = `<i data-lucide="sparkles"></i> Find PGs`;
        }
        
        // Update progress dots
        progressSteps.forEach(stepEl => {
            const stepNum = parseInt(stepEl.dataset.step);
            stepEl.classList.remove("active", "completed");
            
            if (stepNum === currentWizardStep) {
                stepEl.classList.add("active");
            } else if (stepNum < currentWizardStep) {
                stepEl.classList.add("completed");
            }
        });
        
        lucide.createIcons();
    }

    // 5. State Persistence logic (CRITICAL: Preserves ratings)
    function saveWizardState() {
        globalState.gender = document.getElementById("pref-gender").value;
        globalState.room_type = document.getElementById("pref-room-type").value;
        globalState.budget = parseInt(budgetSlider.value);
        
        // Priorities (1 to 10)
        globalState.priorities.cost = parseInt(ratings.cost.value);
        globalState.priorities.distance = parseInt(ratings.distance.value);
        globalState.priorities.safety = parseInt(ratings.safety.value);
        globalState.priorities.quality = parseInt(ratings.quality.value);
        globalState.priorities.amenities = parseInt(ratings.amenities.value);
        
        // Amenities (booleans)
        globalState.amenities.wifi = document.getElementById("pref-wifi").checked;
        globalState.amenities.ac = document.getElementById("pref-ac").checked;
        globalState.amenities.food = document.getElementById("pref-food").checked;
        globalState.amenities.laundry = document.getElementById("pref-laundry").checked;
        globalState.amenities.parking = document.getElementById("pref-parking").checked;
    }

    function prefillWizardFromState() {
        // Pre-fill Step 1 Constraints
        document.getElementById("pref-gender").value = globalState.gender;
        document.getElementById("pref-room-type").value = globalState.room_type;
        budgetSlider.value = globalState.budget;
        budgetValueLabel.textContent = `₹${globalState.budget.toLocaleString('en-IN')} max`;
        
        // Pre-fill Step 2 Priorities
        Object.keys(ratings).forEach(key => {
            ratings[key].value = globalState.priorities[key];
            ratingLabels[key].textContent = `${globalState.priorities[key]} / 10`;
        });
        
        // Pre-fill Step 3 Amenities
        document.getElementById("pref-wifi").checked = globalState.amenities.wifi;
        document.getElementById("pref-ac").checked = globalState.amenities.ac;
        document.getElementById("pref-food").checked = globalState.amenities.food;
        document.getElementById("pref-laundry").checked = globalState.amenities.laundry;
        document.getElementById("pref-parking").checked = globalState.amenities.parking;
    }

    function openWizardModal(isEditMode = true) {
        prefillWizardFromState();
        goToStep(1); // Start at step 1
        
        wizardOverlay.classList.add("open");
        
        if (isEditMode) {
            closeWizardBtn.classList.remove("hidden");
            wizardTitle.textContent = "Modify Priorities";
        } else {
            closeWizardBtn.classList.add("hidden");
            wizardTitle.textContent = "Find your Best PG";
        }
    }

    function closeWizardModal() {
        wizardOverlay.classList.remove("open");
    }

    // 6. Modify button triggers Modal open
    btnEditPriorities.addEventListener("click", () => {
        openWizardModal(true);
    });

    // 7. Results Page Algorithm Toggles (WSM vs TOPSIS)
    algMiniTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            algMiniTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            globalState.algorithm = tab.dataset.alg;
            loadRecommendations();
        });
    });

    // 8. Load Recommendations API Call
    async function loadRecommendations() {
        listingsGrid.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Calculating scores and ranking accommodations...</p>
            </div>
        `;

        // Render top Priority Summary Banner
        renderSummaryBanner();

        // Convert 1-10 priority ratings into normalized weights
        // Apply power scaling (priority²) so higher-rated criteria become truly dominant
        // e.g. distance=10, others=5 → squared: 100,25,25,25,25 → distance gets 50% weight
        const priorities = globalState.priorities;
        const PRIORITY_POWER = 2;
        const scaledCost = Math.pow(priorities.cost, PRIORITY_POWER);
        const scaledDistance = Math.pow(priorities.distance, PRIORITY_POWER);
        const scaledSafety = Math.pow(priorities.safety, PRIORITY_POWER);
        const scaledQuality = Math.pow(priorities.quality, PRIORITY_POWER);
        const scaledAmenities = Math.pow(priorities.amenities, PRIORITY_POWER);
        const totalScaled = scaledCost + scaledDistance + scaledSafety + scaledQuality + scaledAmenities;
        
        const weights = {
            cost: totalScaled > 0 ? (scaledCost / totalScaled) : 0.2,
            distance: totalScaled > 0 ? (scaledDistance / totalScaled) : 0.2,
            safety: totalScaled > 0 ? (scaledSafety / totalScaled) : 0.2,
            quality: totalScaled > 0 ? (scaledQuality / totalScaled) : 0.2,
            amenities: totalScaled > 0 ? (scaledAmenities / totalScaled) : 0.2
        };

        const payload = {
            preferences: {
                gender: globalState.gender,
                room_type: globalState.room_type,
                budget: globalState.budget,
                wifi: globalState.amenities.wifi,
                ac: globalState.amenities.ac,
                food: globalState.amenities.food,
                laundry: globalState.amenities.laundry,
                parking: globalState.amenities.parking
            },
            weights: weights,
            algorithm: globalState.algorithm
        };

        try {
            const res = await fetch("/api/recommend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("API recommendation request failed");

            const data = await res.json();
            loadedAccommodations = data;
            renderRecommendations(data);
        } catch (error) {
            console.error("Error fetching recommendation ratings:", error);
            listingsGrid.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="alert-triangle"></i>
                    <h3>API Communication Failed</h3>
                    <p>Failed to retrieve recommendation rankings. Check if backend server is active.</p>
                </div>
            `;
            lucide.createIcons();
        }
    }

    function renderSummaryBanner() {
        summaryGender.textContent = globalState.gender === "male" ? "Boys / Gents PG" : "Girls / Ladies PG";
        summaryRoom.textContent = globalState.room_type === "any" ? "Any Room Sharing" : `${globalState.room_type} Room`;
        summaryBudget.textContent = `Rent ≤ ₹${globalState.budget.toLocaleString('en-IN')}`;

        // Priorities summary list
        const pr = globalState.priorities;
        summaryPrioritiesList.innerHTML = `
            <div class="summary-priority-badge">Cost: <span>${pr.cost}/10</span></div>
            <div class="summary-priority-badge">Distance: <span>${pr.distance}/10</span></div>
            <div class="summary-priority-badge">Safety: <span>${pr.safety}/10</span></div>
            <div class="summary-priority-badge">Quality: <span>${pr.quality}/10</span></div>
            <div class="summary-priority-badge">Amenities: <span>${pr.amenities}/10</span></div>
        `;
    }

    // 9. Render Recommendations Grid
    function renderRecommendations(listings) {
        if (!listings || listings.length === 0) {
            resultsCountLabel.textContent = "Showing 0 matching options";
            listingsGrid.innerHTML = `
                <div class="empty-state">
                    <i data-lucide="search-x"></i>
                    <h3>No Accommodations Match Your Hard Filters</h3>
                    <p>Try increasing your budget or changing the room sharing option.</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        resultsCountLabel.textContent = `Showing ${listings.length} matching options`;
        listingsGrid.innerHTML = "";

        listings.forEach((pg, index) => {
            const card = document.createElement("div");
            card.className = "pg-card";
            card.dataset.id = pg.pg_id;

            const isCompared = selectedForCompare.some(item => item.pg_id === pg.pg_id);
            const scorePct = Math.round(pg.score * 100);

            card.innerHTML = `
                <div class="card-image-section">
                    <div class="card-image-bg"></div>
                    ${pg.photo_url ? 
                        `<img src="${pg.photo_url}" alt="${pg.pg_name}" class="pg-card-img" onerror="this.outerHTML='<svg width=\\'120\\' height=\\'90\\' viewBox=\\'0 0 100 80\\' fill=\\'none\\' xmlns=\\'http://www.w3.org/2000/svg\\' style=\\'z-index: 1;\\'><path d=\\'M10 50 L50 20 L90 50 Z\\' fill=\\'#ff5a3c\\' fill-opacity=\\'0.9\\'/><rect x=\\'25\\' y=\\'45\\' width=\\'50\\' height=\\'30\\' fill=\\'#e2e8f0\\'/><rect x=\\'40\\' y=\\'55\\' width=\\'20\\' height=\\'20\\' fill=\\'#334155\\'/><circle cx=\\'50\\' cy=\\'35\\' r=\\'5\\' fill=\\'#f8fafc\\'/></svg>'">` 
                        : 
                        `<svg width="120" height="90" viewBox="0 0 100 80" fill="none" xmlns="http://www.w3.org/2000/svg" style="z-index: 1;">
                            <path d="M10 50 L50 20 L90 50 Z" fill="#ff5a3c" fill-opacity="0.9"/>
                            <rect x="25" y="45" width="50" height="30" fill="#e2e8f0"/>
                            <rect x="40" y="55" width="20" height="20" fill="#334155"/>
                            <circle cx="50" cy="35" r="5" fill="#f8fafc"/>
                        </svg>`
                    }
                    <div class="price-tag">₹${parseInt(pg.monthly_rent).toLocaleString('en-IN')}<span style="font-size:10px; font-weight:500;">/mo</span></div>
                    <div class="rank-badge">Rank #${index + 1}</div>
                    <div class="match-score-badge">${scorePct}% Match</div>
                    <button class="heart-btn" title="Add to Favorites"><i data-lucide="heart"></i></button>
                </div>
                
                <div class="card-details-section">
                    <h3 class="card-pg-name" title="${pg.pg_name}">${pg.pg_name}</h3>
                    <div class="card-pg-address">
                        <i data-lucide="map-pin"></i>
                        <span>${pg.locality}, ${pg.nearest_bus_stop}</span>
                    </div>
                    
                    <div class="card-specs-row">
                        <div class="spec-item" title="Room Type">
                            <i data-lucide="user"></i>
                            <span>${pg.room_type}</span>
                        </div>
                        <div class="spec-item" title="Bathroom type">
                            <i data-lucide="bath"></i>
                            <span>${pg.bathroom_type} Bath</span>
                        </div>
                        <div class="spec-item" title="Distance to college">
                            <i data-lucide="milestone"></i>
                            <span>${pg.distance_to_bmsit_km} km</span>
                        </div>
                    </div>
                    
                    <!-- Match Score Breakdown Bars -->
                    <div class="card-breakdown">
                        <div class="breakdown-title">Decision breakdown</div>
                        
                        <div class="breakdown-row">
                            <div class="breakdown-label"><i data-lucide="indian-rupee"></i> Cost</div>
                            <div class="breakdown-bar-bg">
                                <div class="breakdown-bar-fill cost" style="width: ${Math.round(pg.subscores.sub_cost * 100)}%;"></div>
                            </div>
                            <div class="breakdown-val">${Math.round(pg.subscores.sub_cost * 100)}%</div>
                        </div>

                        <div class="breakdown-row">
                            <div class="breakdown-label"><i data-lucide="milestone"></i> Distance</div>
                            <div class="breakdown-bar-bg">
                                <div class="breakdown-bar-fill distance" style="width: ${Math.round(pg.subscores.sub_dist * 100)}%;"></div>
                            </div>
                            <div class="breakdown-val">${Math.round(pg.subscores.sub_dist * 100)}%</div>
                        </div>

                        <div class="breakdown-row">
                            <div class="breakdown-label"><i data-lucide="shield"></i> Safety</div>
                            <div class="breakdown-bar-bg">
                                <div class="breakdown-bar-fill safety" style="width: ${Math.round(pg.subscores.sub_safety * 100)}%;"></div>
                            </div>
                            <div class="breakdown-val">${Math.round(pg.subscores.sub_safety * 100)}%</div>
                        </div>

                        <div class="breakdown-row">
                            <div class="breakdown-label"><i data-lucide="star"></i> Quality</div>
                            <div class="breakdown-bar-bg">
                                <div class="breakdown-bar-fill quality" style="width: ${Math.round(pg.subscores.sub_quality * 100)}%;"></div>
                            </div>
                            <div class="breakdown-val">${Math.round(pg.subscores.sub_quality * 100)}%</div>
                        </div>

                        <div class="breakdown-row">
                            <div class="breakdown-label"><i data-lucide="smile"></i> Amenities</div>
                            <div class="breakdown-bar-bg">
                                <div class="breakdown-bar-fill amenity" style="width: ${Math.round(pg.subscores.sub_amenity * 100)}%;"></div>
                            </div>
                            <div class="breakdown-val">${Math.round(pg.subscores.sub_amenity * 100)}%</div>
                        </div>
                    </div>

                    <div class="card-actions-row">
                        <label class="compare-checkbox-label">
                            <input type="checkbox" class="compare-checkbox" ${isCompared ? 'checked' : ''}>
                            <span class="compare-box-custom"></span>
                            <span>Compare</span>
                        </label>
                        <button class="btn btn-outline btn-sm btn-view-details">View Details</button>
                    </div>
                </div>
            `;

            listingsGrid.appendChild(card);
            
            // View Details event
            card.querySelector(".btn-view-details").addEventListener("click", () => {
                showDetailsModal(pg);
            });

            // Compare event
            const checkbox = card.querySelector(".compare-checkbox");
            checkbox.addEventListener("change", (e) => {
                handleCompareToggle(pg, e.target.checked);
            });
            
            // Favorites heart event
            const heartBtn = card.querySelector(".heart-btn");
            heartBtn.addEventListener("click", () => {
                heartBtn.classList.toggle("active");
                if (heartBtn.classList.contains("active")) {
                    heartBtn.innerHTML = `<i data-lucide="heart" fill="var(--primary)"></i>`;
                } else {
                    heartBtn.innerHTML = `<i data-lucide="heart"></i>`;
                }
                lucide.createIcons();
            });
        });

        lucide.createIcons();
    }

    // 10. Comparison Logic
    function handleCompareToggle(pg, checked) {
        if (checked) {
            if (selectedForCompare.length >= 3) {
                alert("You can compare a maximum of 3 PGs at a time.");
                const checkbox = document.querySelector(`.pg-card[data-id="${pg.pg_id}"] .compare-checkbox`);
                if (checkbox) checkbox.checked = false;
                return;
            }
            selectedForCompare.push(pg);
        } else {
            selectedForCompare = selectedForCompare.filter(item => item.pg_id !== pg.pg_id);
        }
        updateCompareDrawer();
    }

    function updateCompareDrawer() {
        const count = selectedForCompare.length;
        compareCountLabel.textContent = count;

        if (count > 0) {
            compareDrawer.classList.add("open");
            compareThumbnails.innerHTML = "";

            selectedForCompare.forEach(pg => {
                const thumb = document.createElement("div");
                thumb.className = "compare-thumb-card";
                thumb.innerHTML = `
                    <span class="compare-thumb-name" title="${pg.pg_name}">${pg.pg_name}</span>
                    <button class="compare-thumb-remove" data-id="${pg.pg_id}">&times;</button>
                `;
                compareThumbnails.appendChild(thumb);

                thumb.querySelector(".compare-thumb-remove").addEventListener("click", () => {
                    selectedForCompare = selectedForCompare.filter(item => item.pg_id !== pg.pg_id);
                    const checkbox = document.querySelector(`.pg-card[data-id="${pg.pg_id}"] .compare-checkbox`);
                    if (checkbox) checkbox.checked = false;
                    
                    updateCompareDrawer();
                });
            });

            if (count >= 2) {
                compareNowBtn.removeAttribute("disabled");
                compareNowBtn.style.opacity = 1;
            } else {
                compareNowBtn.setAttribute("disabled", "true");
                compareNowBtn.style.opacity = 0.5;
            }
        } else {
            compareDrawer.classList.remove("open");
        }
    }

    clearCompareBtn.addEventListener("click", () => {
        document.querySelectorAll(".compare-checkbox").forEach(box => box.checked = false);
        selectedForCompare = [];
        updateCompareDrawer();
    });

    closeDrawerBtn.addEventListener("click", () => {
        compareDrawer.classList.remove("open");
    });

    compareNowBtn.addEventListener("click", () => {
        if (selectedForCompare.length < 2) return;

        // Populate table heads
        compareTableHead.innerHTML = `<th class="compare-header-cell">Attribute / Objective</th>`;
        selectedForCompare.forEach(pg => {
            const scorePct = Math.round(pg.score * 100);
            compareTableHead.innerHTML += `
                <th>
                    <div class="compare-title-bold">${pg.pg_name}</div>
                    <div style="margin-top: 5px;"><span class="compare-score-badge">${scorePct}% Match</span></div>
                </th>
            `;
        });

        const attributes = [
            { label: "Recommendation Score", key: "score", format: v => `${Math.round(v * 100)}%` },
            { label: "Monthly Rent", key: "monthly_rent", format: v => `₹${parseInt(v).toLocaleString('en-IN')}` },
            { label: "Security Deposit", key: "security_deposit", format: v => `₹${parseInt(v).toLocaleString('en-IN')}` },
            { label: "Room Sharing", key: "room_type", format: v => v },
            { label: "Bathroom Access", key: "bathroom_type", format: v => `${v} Bathroom` },
            { label: "Distance to BMSIT", key: "distance_to_bmsit_km", format: v => `${v} km` },
            { label: "Distance to Bus Stop", key: "distance_to_bus_stop_km", format: v => `${v} km` },
            { label: "Nearest Metro", key: "nearest_metro", format: v => `${v} (${pg => pg.distance_to_metro_km} km)` },
            { label: "Safety Rating", key: "locality_safety_rating", format: v => `★ ${v} / 5` },
            { label: "Overall Student Rating", key: "overall_student_rating", format: v => `★ ${v} / 5` },
            { label: "Landlord Responsiveness", key: "landlord_responsiveness_rating", format: v => `★ ${v} / 5` },
            { label: "Food Rating", key: "food_rating", format: v => `★ ${v} / 5` },
            { label: "WiFi", key: "wifi", format: v => v ? "Yes (Included)" : "No" },
            { label: "AC Available", key: "ac", format: v => v ? "Yes" : "No" },
            { label: "Meals Included", key: "food_included", format: v => v ? "Yes" : "No" },
            { label: "Laundry", key: "laundry", format: v => v ? "Yes" : "No" },
            { label: "Parking", key: "parking", format: v => v ? "Yes" : "No" },
            { label: "Student Community", key: "student_community_present", format: v => v ? "Yes" : "No" }
        ];

        compareTableBody.innerHTML = "";
        attributes.forEach(attr => {
            let rowHtml = `<tr><td class="compare-title-bold">${attr.label}</td>`;
            selectedForCompare.forEach(pg => {
                let val = pg[attr.key];
                let text = "";
                if (attr.key === "nearest_metro") {
                    text = `${pg.nearest_metro} (${pg.distance_to_metro_km} km)`;
                } else {
                    text = attr.format(val);
                }
                rowHtml += `<td>${text}</td>`;
            });
            rowHtml += `</tr>`;
            compareTableBody.innerHTML += rowHtml;
        });

        openModal(compareModal);
    });

    // 11. Detail modal rendering
    function showDetailsModal(pg) {
        modalPgName.textContent = pg.pg_name;
        
        const hasWifi = pg.wifi ? 'present' : 'absent';
        const hasAc = pg.ac ? 'present' : 'absent';
        const hasFood = pg.food_included ? 'present' : 'absent';
        const hasLaundry = pg.laundry ? 'present' : 'absent';
        const hasParking = pg.parking ? 'present' : 'absent';

        modalDetailsContent.innerHTML = `
            <div class="details-grid">
                ${pg.photo_url ? `<div class="details-image-container"><img src="${pg.photo_url}" class="details-modal-img" alt="${pg.pg_name}"></div>` : ''}
                <div class="details-header-block">
                    <div class="details-title-row">
                        <div>
                            <span class="hero-tag" style="margin-bottom:8px;">${pg.gender.toUpperCase()} PG</span>
                            <p style="color:var(--text-muted); font-size:14px;"><i data-lucide="map-pin" style="width:14px; height:14px; display:inline-block; vertical-align:text-bottom;"></i> ${pg.full_address}</p>
                        </div>
                        <div class="details-price-badge">₹${parseInt(pg.monthly_rent).toLocaleString('en-IN')}<span style="font-size:12px; font-weight:500;">/mo</span></div>
                    </div>
                </div>

                <div class="details-meta-list">
                    <div class="details-meta-item"><strong>Room Configuration:</strong> ${pg.room_type} Room</div>
                    <div class="details-meta-item"><strong>Security Deposit:</strong> ₹${parseInt(pg.security_deposit).toLocaleString('en-IN')}</div>
                    <div class="details-meta-item"><strong>Bathroom Type:</strong> ${pg.bathroom_type} Bathroom</div>
                    <div class="details-meta-item"><strong>Additional Charges:</strong> ${pg.additional_charges}</div>
                    <div class="details-meta-item"><strong>Distance to BMSIT:</strong> ${pg.distance_to_bmsit_km} km</div>
                    <div class="details-meta-item"><strong>Locality:</strong> ${pg.locality}</div>
                </div>

                <div>
                    <h4 style="margin-bottom:12px;">Ratings Summary</h4>
                    <div class="card-breakdown" style="background-color:var(--bg-light); padding:20px; border-radius:var(--border-radius-md); border:1px solid var(--border-color);">
                        <div class="breakdown-row">
                            <div class="breakdown-label">Overall Student</div>
                            <div class="breakdown-bar-bg"><div class="breakdown-bar-fill quality" style="width: ${pg.overall_student_rating * 20}%;"></div></div>
                            <div class="breakdown-val">${pg.overall_student_rating} ★</div>
                        </div>
                        <div class="breakdown-row">
                            <div class="breakdown-label">Safety Score</div>
                            <div class="breakdown-bar-bg"><div class="breakdown-bar-fill safety" style="width: ${pg.locality_safety_rating * 20}%;"></div></div>
                            <div class="breakdown-val">${pg.locality_safety_rating} ★</div>
                        </div>
                        <div class="breakdown-row">
                            <div class="breakdown-label">Landlord Support</div>
                            <div class="breakdown-bar-bg"><div class="breakdown-bar-fill distance" style="width: ${pg.landlord_responsiveness_rating * 20}%;"></div></div>
                            <div class="breakdown-val">${pg.landlord_responsiveness_rating} ★</div>
                        </div>
                        <div class="breakdown-row">
                            <div class="breakdown-label">Meals Quality</div>
                            <div class="breakdown-bar-bg"><div class="breakdown-bar-fill cost" style="width: ${pg.food_rating * 20}%;"></div></div>
                            <div class="breakdown-val">${pg.food_rating} ★</div>
                        </div>
                    </div>
                </div>

                <div>
                    <h4 style="margin-bottom:12px;">Amenities & Infrastructure</h4>
                    <div class="details-amenities-list">
                        <div class="details-amenity-badge ${hasWifi}">
                            <i data-lucide="${pg.wifi ? 'check' : 'x'}"></i> WiFi Internet
                        </div>
                        <div class="details-amenity-badge ${hasAc}">
                            <i data-lucide="${pg.ac ? 'check' : 'x'}"></i> Air Conditioning
                        </div>
                        <div class="details-amenity-badge ${hasFood}">
                            <i data-lucide="${pg.food_included ? 'check' : 'x'}"></i> Daily Meals
                        </div>
                        <div class="details-amenity-badge ${hasLaundry}">
                            <i data-lucide="${pg.laundry ? 'check' : 'x'}"></i> Laundry Operations
                        </div>
                        <div class="details-amenity-badge ${hasParking}">
                            <i data-lucide="${pg.parking ? 'check' : 'x'}"></i> Secure Parking
                        </div>
                    </div>
                </div>

                ${parseFloat(pg.distance_to_bmsit_km) > 1.0 ? `
                <div>
                    <h4 style="margin-bottom:12px;">Transit & Routing Pathway</h4>
                    <div class="routing-diagram-container">
                        <div class="routing-title">Travel from BMSIT Campus</div>
                        <div class="routing-flow">
                            <div class="routing-node active">
                                <div class="routing-circle"><i data-lucide="graduation-cap" style="width:14px; height:14px;"></i></div>
                                <span class="routing-label">BMSIT</span>
                            </div>
                            <div class="routing-line">
                                <div class="routing-dist">${pg.distance_to_bmsit_km} km</div>
                            </div>
                            
                            <div class="routing-node">
                                <div class="routing-circle"><i data-lucide="bus" style="width:14px; height:14px;"></i></div>
                                <span class="routing-label" style="text-align:center;">${pg.nearest_bus_stop}</span>
                            </div>
                            <div class="routing-line">
                                <div class="routing-dist">${pg.distance_to_bus_stop_km} km</div>
                            </div>
                            
                            <div class="routing-node active">
                                <div class="routing-circle"><i data-lucide="home" style="width:14px; height:14px;"></i></div>
                                <span class="routing-label">PG Residence</span>
                            </div>
                        </div>
                    </div>
                </div>
                ` : ''}
                
                <div style="margin-top:15px; text-align:center;">
                    <a href="${pg.google_maps_url || pg.verification_link}" target="_blank" class="btn btn-primary" style="text-decoration:none;">
                        <i data-lucide="external-link"></i> View Location on Google Maps
                    </a>
                </div>
            </div>
        `;

        openModal(detailsModal);
        lucide.createIcons();
    }

    // Modal Helpers
    function openModal(modal) {
        modal.classList.add("open");
    }

    function closeModal() {
        compareModal.classList.remove("open");
        detailsModal.classList.remove("open");
        closeWizardModal();
    }

    closeModalBtns.forEach(btn => btn.addEventListener("click", closeModal));
    window.addEventListener("click", (e) => {
        if (e.target === compareModal || e.target === detailsModal) closeModal();
    });

    // SPA View Router
    function showView(viewId) {
        // Hide all views
        const views = ["home", "recommender", "analytics", "methodology"];
        views.forEach(id => {
            const section = document.getElementById(id);
            if (section) section.classList.add("hidden");
            
            const link = document.querySelector(`.nav-link[href="#${id}"]`);
            if (link) link.classList.remove("active");
        });
        
        // Show selected view
        const activeSection = document.getElementById(viewId);
        if (activeSection) {
            activeSection.classList.remove("hidden");
        }
        
        const activeLink = document.querySelector(`.nav-link[href="#${viewId}"]`);
        if (activeLink) activeLink.classList.add("active");
        
        // If switching to Recommender and listings are empty, load them
        if (viewId === "recommender" && loadedAccommodations.length === 0) {
            loadRecommendations();
        }
        
        // If switching to Analytics, render charts
        if (viewId === "analytics") {
            if (marketStats) {
                renderCharts(marketStats);
            }
        }
        
        // Close wizard modal just in case it is open when they switch tabs
        closeWizardModal();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // 12. Navigation Actions for Dashboard Tab
    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const viewId = link.getAttribute("href").substring(1);
            showView(viewId);
        });
    });

    closeAnalyticsBtn.addEventListener("click", () => {
        showView("home");
    });

    // 13. Fetch stats and render analytical Charts (Chart.js)
    async function fetchStats() {
        try {
            const res = await fetch("/api/stats");
            if (!res.ok) throw new Error("Stats request failed");
            
            const stats = await res.json();
            marketStats = stats;
            
            document.getElementById("stat-total-pgs").textContent = stats.total_pgs;
            document.getElementById("stat-avg-rent").textContent = `₹${Math.round(stats.avg_rent).toLocaleString('en-IN')}`;
            document.getElementById("stat-avg-safety").textContent = `${stats.avg_safety} / 5.0`;
            document.getElementById("stat-avg-rating").textContent = `${stats.overall_student_rating || stats.avg_student_rating} / 5.0`;
            
        } catch (error) {
            console.error("Failed to load dashboard statistics:", error);
        }
    }

    function renderCharts(stats) {
        const ctxRoomType = document.getElementById("rentRoomTypeChart").getContext("2d");
        const ctxDistance = document.getElementById("rentDistanceChart").getContext("2d");

        if (rentRoomTypeChart) rentRoomTypeChart.destroy();
        if (rentDistanceChart) rentDistanceChart.destroy();

        const roomTypes = Object.keys(stats.avg_rent_by_room_type);
        const avgRents = Object.values(stats.avg_rent_by_room_type);

        rentRoomTypeChart = new Chart(ctxRoomType, {
            type: "bar",
            data: {
                labels: roomTypes,
                datasets: [{
                    label: "Average Monthly Rent (₹)",
                    data: avgRents,
                    backgroundColor: [
                        "rgba(255, 90, 60, 0.75)",
                        "rgba(6, 182, 212, 0.75)",
                        "rgba(139, 92, 246, 0.75)",
                        "rgba(16, 185, 129, 0.75)"
                    ],
                    borderColor: [
                        "#ff5a3c",
                        "#06b6d4",
                        "#8b5cf6",
                        "#10b981"
                    ],
                    borderWidth: 1.5,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) { return "₹" + value.toLocaleString(); }
                        }
                    }
                }
            }
        });

        // Scatter Coordinate dataset
        const scatterData = loadedAccommodations.map(pg => ({
            x: parseFloat(pg.distance_to_bmsit_km),
            y: parseInt(pg.monthly_rent),
            label: pg.pg_name
        }));

        rentDistanceChart = new Chart(ctxDistance, {
            type: "scatter",
            data: {
                datasets: [{
                    label: "PG Accommodation",
                    data: scatterData,
                    backgroundColor: "rgba(255, 90, 60, 0.7)",
                    borderColor: "#ff5a3c",
                    borderWidth: 1,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const pt = context.raw;
                                return `${pt.label}: ₹${pt.y.toLocaleString()} at ${pt.x} km`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: "Distance to BMSIT Campus (km)", font: { weight: 'bold' } }
                    },
                    y: {
                        title: { display: true, text: "Monthly Rent (₹)", font: { weight: 'bold' } },
                        ticks: {
                            callback: function(value) { return "₹" + value.toLocaleString(); }
                        }
                    }
                }
            }
        });
    }
});
