# Piling QA Dashboard (Early Prototype)

This dashboard lets you:
1. Upload design data (LandXML `.xml`, DXF `.dxf`, or Leica `.lok`).
2. See the design points in:
   - Local 2D Plan View (Easting vs Northing, CAD-style)
   - 3D Orbit View (zoom, rotate, inspect Elevation)

Later phases will add:
- As-built CSV upload
- Deviation checks
- Pile detail profiles (depth vs time)
- Map/satellite background with georeferenced coordinates

---

## 📦 What's in this bundle
- `app.py` — Streamlit app code
- `requirements.txt` — Python libraries needed
- `rig_image.jpg` — Placeholder image for the home screen
- `README.md` — This file

---

## ▶ Run it locally (for testing)

1. Install Python 3.10+ if you don't already have it.

2. Open a terminal / command prompt in the folder containing these files.

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the dashboard:
   ```bash
   streamlit run app.py
   ```

5. Your browser will open automatically (if not, it will print a local URL you can click).

---

## 🌍 Put it on the web (Streamlit Cloud)

You will upload these four files to a GitHub repo, then let Streamlit Cloud deploy it for you.
No coding required — just drag and drop.

### Step 1. Create a GitHub repo
1. Go to https://github.com/new
2. Repository name: `piling-dashboard`
3. Make it **Public**
4. Tick "Add a README file"
5. Click **Create repository**

### Step 2. Upload the files
1. On your new repo page, click **Add file → Upload files**
2. Drag in:
   - `app.py`
   - `requirements.txt`
   - `rig_image.jpg`
   - `README.md`
3. Scroll down and click **Commit changes** (green button)

### Step 3. Deploy on Streamlit Cloud
1. Go to https://share.streamlit.io
2. Sign in with GitHub (same account)
3. Click **New app**
4. Select your repo `piling-dashboard`
5. For "Main file path", enter:
   ```
   app.py
   ```
6. Click **Deploy**

After build, you'll get a public link like:
`https://piling-dashboard-yourname.streamlit.app`

Share that link with your team. They can:
- Upload a LandXML / DXF / LOK
- See the design points in 2D and 3D

---

## 📌 Notes / Limitations in this version

- Map/satellite overlay:
  Right now we show a CAD-style local plan (Easting/Northing) and a 3D orbit. A satellite basemap ("Google Earth style") needs real-world lat/long coordinates or a known transform from your project grid to WGS84. We'll add that once you confirm what coordinate system you're using in the field.

- .lok parsing:
  We treat `.lok` as a ZIP container and try to read any XML with `<CgPoint>` in it (LandXML style). Some Leica `.lok` files are binary; if that's the case, we will fall back to LandXML input instead.

- DXF parsing:
  We grab POINT entities and block INSERT locations as design points. If your DXF stores piles in a different layer or as text annotations, we can extend the parser to read those.

- As-built CSV:
  The upload control is on the Home page but it's not yet wired in to the Overview. We'll connect that after you tell us how you want to analyze tolerances / reports.

---

## ✅ Next improvements we can add later

- Overlay design points on a satellite basemap
- Show tolerances (horizontal offset limits, depth achieved vs target)
- Per-pile detail page with depth log and inclination
- Export PDF/Excel "Pile QA Report"
- Color-code points (Pass/Fail)

You're now fully ready for first on-site tests. 🚀
