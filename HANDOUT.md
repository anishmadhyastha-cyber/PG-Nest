# PGNest | Engineering Handover & Project Memory

This document serves as an exhaustive context dump and technical handover for the **PGNest** student accommodation recommender system. It contains the complete architectural, algorithmic, aesthetic, and functional memory of the project.

---

## 1. Project Overview

### What the Project Is
**PGNest** is a multi-objective decision-making recommender system designed specifically for students at **BMSIT & MSRIT** (Yelahanka, Bengaluru) to search, evaluate, and rank Paying Guest (PG) student accommodations. 

### Why It Exists
Finding student housing involves balancing multiple conflicting objectives:
1. **Cost:** Keeping monthly rent and security deposits low.
2. **Proximity:** Living as close to campus as possible.
3. **Safety:** Securing accommodation in highly safe areas.
4. **Quality:** Selecting highly rated landlords and quality services.
5. **Amenities:** Ensuring critical amenities (WiFi, AC, food, laundry, parking) are available.

Standard housing search portals list properties in flat tables or simple filter grids, leaving the complex trade-off analysis to the student. PGNest solves this by applying mathematical Multi-Criteria Decision Analysis (MCDA) algorithms to rank properties based on custom student priority weight profiles.

### Intended Emotional Experience
* **Reassurance & Clarity:** Reducing the anxiety of finding accommodation in a new city.
* **Empowerment & Control:** Giving students precise sliders to define exactly what they care about most.
* **Premium Care:** Transitioning the process from a tedious search to an executive, personalized concierge match.

### Target Aesthetic & Design Language
* **Modern Warm Real-Estate Theme:** Primary highlight color is a vibrant real-estate orange (`#ff5a3c`), contrasted with a deep space navy (`#1a1e25`) and soft background greys.
* **Premium Interactions:** Subtle drop shadows (`--shadow-hover`), smooth transform transitions on hover, custom-styled slider inputs, interactive checkbox cards, and responsive modals.
* **Information Density & Micro-Visualizations:** Cards do not just show scores; they render comparative progress bars representing how well a PG met each individual criteria (Cost, Distance, Safety, Quality, Amenities) alongside a structured transit routing pathway.

---

## 2. Current Tech Stack

| Component | Technology | Detail / Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** (Python 3.11+) | Asynchronous Python framework serving the `/api/recommend` and `/api/stats` JSON endpoints, as well as mounting the frontend static directory. |
| **Data Processing** | **Pandas** & **NumPy** | Performs raw CSV parsing, column cleanup, boolean mapping, and matrix mathematics for the MCDA recommendation algorithms. |
| **Frontend Stack** | **Vanilla HTML5, CSS3, ES6 JavaScript** | Keeping the client extremely fast, dependency-free, and simple to render directly from the FastAPI server. |
| **Data Storage** | **Flat CSV (`data.csv`)** | A local database of 70 realistic PG listings around Yelahanka with properties like rent, campus distance, coordinates, and ratings. |
| **Charts** | **Chart.js** (via CDN) | Generates dynamic visualizations on the Analytics Dashboard (e.g., Rent vs. Distance scatter plots and rent distributions). |
| **Iconography** | **Lucide Icons** (via CDN) | Renders clean, lightweight vector icons inline. |
| **Typography** | **Google Fonts** | Imports the modern neo-grotesque `Inter` font for UI elements and the geometric humanist `Outfit` font for headlines and cards. |

---

## 3. Current Project Status

### What Currently Works
1. **Interactive Onboarding Wizard:** A beautiful 3-step modal guide that collects:
   * **Constraints (Step 1):** Hard filters on Gender Group, Room Type, and Maximum Rent.
   * **Priorities (Step 2):** Objective weight ratings from 1 to 10 for Cost, Distance, Safety, Quality, and Amenities.
   * **Amenities (Step 3):** Boolean requirements for specific features.
2. **MCDA Recommendation Engine:** Implements two distinct ranking algorithms on the backend:
   * **WSM (Weighted Sum Model):** Simple linear weighted combination of normalized scores.
   * **TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution):** Vector-normalizes criteria, constructs weighted matrices, evaluates Euclidean distances to positive-ideal and negative-ideal alternatives, and ranks by relative closeness.
3. **Dynamic Score Breakdown:** Cards render live, colored progress bars indicating the subscores for each criteria, helping the user understand *why* a particular PG ranked high.
4. **Side-by-Side Comparison:** A floating bottom drawer displays up to 3 selected properties. Clicking "Compare Now" opens a comparison table modal summarizing attributes side-by-side.
5. **Transit Routing Visualization:** Property details modals show a visual pathway diagram from the BMSIT campus to the nearest bus stop and ultimately the PG, displaying step-by-step distances.
6. **Analytics Dashboard:** Visualizes overall market statistics using Chart.js, including average rents, safety index, and distribution charts.
7. **Automated Integration Tests:** `backend/test_api.py` utilizes FastAPI `TestClient` to verify the mathematical correctness and constraint filtering of the API endpoints.

### What Needs Work / Future Backlog
* **Persistent Favorites:** Introduce local storage caching or session profiles so students don't lose favorited PGs on reload.
* **Active Listing Form:** Implement backend routes for the "List a PG" button, allowing landlords to input data that Appends to the CSV database.
* **Real-time Map Integration:** Upgrade the static Google Maps link to an interactive Leaflet/Mapbox map highlighting the transit path and PG locations.
* **Database Migration:** Move from `data.csv` to an active database (SQLAlchemy + SQLite/PostgreSQL) as listing volume grows.

---

## 4. Detailed File & Folder Structure

```
PG-Nest/
├── data.csv                        # Main CSV file with 70 PG accommodation listings
├── recommender_system.ipynb        # Jupyter Notebook used for initial data research and tests
├── backend/
│   ├── app.py                      # Core FastAPI app (calculates WSM, TOPSIS, serves endpoints)
│   ├── test_api.py                 # Automated integration tests for recommendation logic
│   └── static/
│       ├── index.html              # Main HTML skeleton, modals, layouts, and page panels
│       ├── styles.css              # Custom styling sheet (CSS variables, layout, animations)
│       └── app.js                  # Frontend controllers, dynamic DOM renders, and Chart.js code
```

### Major File Explanations

#### 1. [`backend/app.py`](file:///d:/git/PG-Nest/backend/app.py)
This is the heart of the system. On startup, it loads `data.csv` and preprocesses it:
* Maps text fields ("Yes"/"No") to booleans.
* Infers gender group compatibility using a keyword heuristic from the PG name (e.g., "lady", "ladies", "girl" -> female; "boys", "gents" -> male). If no keyword matches, it uses an odd/even PG ID heuristic.
* Cleans and fills numeric columns for rent, deposits, and distances.
* **Recommendation API (`/api/recommend`):**
  * Applies **hard filters** (budget, room type, gender) to exclude invalid listings.
  * Standardizes criteria. For WSM, it normalizes relative to min-max bounds (minimizes rent and distance, maximizes safety, quality, and amenity matches).
  * For TOPSIS, it constructs an $m \times 5$ decision matrix, normalizes using vector scaling, multiplies by weights, determines positive-ideal ($A^*$) and negative-ideal ($A^-$) coordinates, calculates Euclidean distances ($S_i^*$ and $S_i^-$), and computes closeness coefficient:
    $$C_i = \frac{S_i^-}{S_i^* + S_i^-}$$
  * Returns the sorted records with individual subscore breakdowns.

#### 2. [`backend/static/app.js`](file:///d:/git/PG-Nest/backend/static/app.js)
Manages the interactive states of the UI:
* **Priority Weight Scaling:** Before sending weights to the backend, it squares the sliders' 1-10 inputs (`Math.pow(val, 2)`). This power-scaling helps critical priorities (e.g. 10/10 safety) mathematically dominate over moderate ones (5/10), reflecting realistic student choices.
* **Wizard State Prefilling & Modification:** Retains the parameters in a `globalState` object, allowing the user to click "Modify Priorities" without losing their previous input.
* **Card Rendering:** Dynamically builds PG cards, attaching custom event listeners to "Compare" checkboxes, the "Favorite" heart button, and the details modal trigger.
* **Comparison Drawer:** Keeps track of selected properties (limit 3) and structures comparison matrix fields dynamically.
* **Chart.js Handler:** Renders a bar chart and scatter plot once the student clicks on the Analytics tab, mapping the coordinate parameters.

#### 3. [`backend/static/styles.css`](file:///d:/git/PG-Nest/backend/static/styles.css)
* Organizes elements using a structured design system with semantic custom CSS variables.
* Implements animations (`fadeIn`, keyframe spin loops) and interactive status colors for progress fills:
  * `--color-cost`: Rose Red (`#f43f5e`)
  * `--color-distance`: Cyan Blue (`#06b6d4`)
  * `--color-safety`: Emerald Green (`#10b981`)
  * `--color-quality`: Yellow (`#eab308`)
  * `--color-amenity`: Purple (`#8b5cf6`)
* Modals utilize a backdrop blur filter (`backdrop-filter: blur(8px)`) and a subtle vertical slide-in transition.

---

## 5. Algorithmic Comparison

When adjusting the algorithm toggle on the results page:

| Aspect | Weighted Sum Model (WSM) | TOPSIS |
| :--- | :--- | :--- |
| **Logic** | Multiplies normalized criteria values directly by weights and sums them up. | Measures how close a property is to the "ideal best" and how far it is from the "ideal worst". |
| **Behavior** | Linear and predictable. Excellent for straightforward preferences. | Non-linear. A property that is consistently average across all criteria can rank higher than one that is perfect in one criteria but terrible in another. |
| **Sensitivity** | Sensitive to extreme criteria values. | Balanced; avoids recommendations with severe weaknesses unless highly weighted. |

---

## 6. Setup & Execution Instructions

Follow these steps to run the application locally:

### Step 1: Install Python Dependencies
Ensure Python 3.11+ is installed. Run the following command to install required packages:
```bash
pip install fastapi uvicorn pandas numpy
```
*(Note: FastAPI requires `jinja2` and `python-multipart` if serving HTML templates, but since we serve a static folder directly, standard fastapi and uvicorn are sufficient).*

### Step 2: Validate Implementation via Integration Tests
Before starting the server, run the integration test suite to verify the algorithms and endpoints:
```bash
python backend/test_api.py
```
A successful output will look like this:
```
Starting FastAPI Integration and Recommender Algorithm Tests...
Testing GET /api/stats...
  [PASS] Stats endpoint passed successfully!
  Total PGs: 70, Average Rent: 9171.43
Testing POST /api/recommend (WSM)...
  [PASS] WSM endpoint passed! Filtered count: 37, Top PG: 'Annapurna PG 67'
Testing POST /api/recommend (TOPSIS)...
  [PASS] TOPSIS endpoint passed! Filtered count: 6, Top PG: 'Sri Sai PG 24'

All Recommender API integration tests passed successfully!
```

### Step 3: Run the Development Server
Navigate into the `backend` folder and launch the Uvicorn web server:
```bash
cd backend
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

### Step 4: Access the Interface
Open your web browser and go to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 7. Known Issues & Technical Debt

1. **Synchronous Data Loading:** The backend loads `data.csv` synchronously on module import. If data size grows to millions of rows, this will block worker startup. It should eventually be loaded asynchronously on application lifespan startup.
2. **Dynamic Gender Heuristics:** The system dynamically infers accommodation gender bounds based on the property name. If a landlord lists "Royal PG 4", it defaults to male because of the even numbered PG identifier. This should be explicitly set in a database column.
3. **No Database Write Safety:** Since data is represented by a single CSV, concurrent landlord listings will create write conflict locks or data overwrite issues. A proper DBMS (SQLite/PostgreSQL) with connection pooling must be added.

---

## 8. Continuation Guidance for Future AIs

When picking up development in a future session:

### Maintain the Cinematic & Emotional Tone
Do not convert this into a boring, plain tabular dashboard. Keep the focus on rich visual indicators:
* Maintain the HSL tailored colors for objective parameters.
* Keep transit routing nodes visual and friendly.
* Ensure the Onboarding Wizard is interactive and modal-based rather than standard text input forms.

### Logic Preservation rules
* **Do NOT change the weight power-scaling logic** (`Math.pow(val, 2)`) in the frontend without thorough testing. Linear weights (1 to 10 mapped to 0.1 to 1.0) do not differentiate priorities well enough in WSM/TOPSIS decisions.
* **Keep algorithm models separate.** The toggle must actively trigger a fresh fetch to `/api/recommend` with the selected algorithm parameter.
* **Hard filters are non-negotiable.** Budget, room type, and gender must remain hard constraints that drop listings before WSM/TOPSIS scores are calculated.
* Check file paths. Ensure `DATA_PATH` is always evaluated relative to the script path (`os.path.dirname(__file__)`) so that the application executes successfully from any execution folder.
