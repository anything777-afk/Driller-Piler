import io
import math
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import ezdxf
except Exception:
    ezdxf = None

st.set_page_config(
    page_title="Piling QA Dashboard",
    layout="wide"
)

# -----------------------------------------------------------------------------
# Session init
# -----------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "home"

if "design_points_df" not in st.session_state:
    st.session_state["design_points_df"] = None

# -----------------------------------------------------------------------------
# Parsers
# -----------------------------------------------------------------------------


def parse_landxml_points(xml_bytes):
    """
    Parse LandXML <CgPoint> entries into a DataFrame with columns:
    Name, Easting, Northing, Elevation
    """
    tree = ET.parse(io.BytesIO(xml_bytes))
    root = tree.getroot()

    # LandXML files often use a namespace like {http://www.landxml.org/schema/LandXML-1.2}
    # We detect it dynamically here.
    ns_uri = root.tag.split('}')[0].strip('{')
    ns = {"lx": ns_uri}

    rows = []
    for cg in root.findall(".//lx:CgPoint", ns):
        name = cg.get("name", "")
        text = (cg.text or "").strip().split()
        if len(text) >= 3:
            try:
                easting = float(text[0])
                northing = float(text[1])
                elev = float(text[2])
                rows.append({
                    "Name": name,
                    "Easting": easting,
                    "Northing": northing,
                    "Elevation": elev,
                    "Source": "LandXML"
                })
            except ValueError:
                continue
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["Name", "Easting", "Northing", "Elevation", "Source"])


def parse_dxf_points(dxf_bytes):
    """
    Parse DXF POINT (and INSERT as fallback) entities into a DataFrame.
    We'll need ezdxf for this to work.
    """
    if ezdxf is None:
        return pd.DataFrame(columns=["Name", "Easting", "Northing", "Elevation", "Source"])

    doc = ezdxf.readmem(dxf_bytes)
    msp = doc.modelspace()

    rows = []

    # 1) POINT entities
    for e in msp.query("POINT"):
        loc = e.dxf.location
        rows.append({
            "Name": f"POINT_{e.dxf.handle}",
            "Easting": float(loc.x),
            "Northing": float(loc.y),
            "Elevation": float(loc.z),
            "Source": "DXF/POINT"
        })

    # 2) INSERT entities (block references)
    # We'll just take the insertion point as a "design point"
    for e in msp.query("INSERT"):
        ip = e.dxf.insert
        rows.append({
            "Name": f"BLK_{e.dxf.name}_{e.dxf.handle}",
            "Easting": float(ip.x),
            "Northing": float(ip.y),
            "Elevation": float(ip.z),
            "Source": "DXF/INSERT"
        })

    if rows:
        return pd.DataFrame(rows)
    else:
        return pd.DataFrame(columns=["Name", "Easting", "Northing", "Elevation", "Source"])


def parse_lok_points(lok_bytes):
    """
    Attempt to parse a Leica .lok project file.

    Many .lok files are actually zip containers that hold design data (often XML).
    We'll try to open as a zip; if successful, we scan all .xml files inside
    and reuse the LandXML parser to grab CgPoints.

    If not a zip, we'll just return empty for now.
    """
    rows = []
    try:
        with zipfile.ZipFile(io.BytesIO(lok_bytes), "r") as zf:
            for name in zf.namelist():
                if name.lower().endswith(".xml"):
                    try:
                        xml_bytes = zf.read(name)
                        df_xml = parse_landxml_points(xml_bytes)
                        if not df_xml.empty:
                            rows.append(df_xml)
                    except Exception:
                        continue
    except zipfile.BadZipFile:
        # not a zip container
        pass

    if rows:
        return pd.concat(rows, ignore_index=True)
    return pd.DataFrame(columns=["Name", "Easting", "Northing", "Elevation", "Source"])


def load_design_file(uploaded_file):
    """
    Detect file type by extension and parse into a design_points DataFrame.
    """
    if uploaded_file is None:
        return None

    fname = uploaded_file.name.lower()

    try:
        raw = uploaded_file.read()
    except Exception:
        # Streamlit sometimes gives a SpooledTemporaryFile that supports .getvalue()
        raw = uploaded_file.getvalue()

    if fname.endswith(".xml"):
        df = parse_landxml_points(raw)
    elif fname.endswith(".dxf"):
        df = parse_dxf_points(raw)
    elif fname.endswith(".lok"):
        df = parse_lok_points(raw)
    else:
        st.error("Unsupported design format. Please upload .xml, .dxf, or .lok")
        return None

    if df is not None and not df.empty:
        # Reset index just to be clean
        df = df.reset_index(drop=True)
    return df


# -----------------------------------------------------------------------------
# Plot builders
# -----------------------------------------------------------------------------

def build_local_plan_view(df):
    """
    Simple CAD-style 2D plan view (no basemap).
    Easting vs Northing, equal aspect.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Easting"],
        y=df["Northing"],
        mode="markers+text",
        text=df["Name"],
        textposition="top center",
        marker=dict(size=8),
        name="Design Points"
    ))

    fig.update_layout(
        title="Local 2D Plan View (Design Points)",
        xaxis_title="Easting",
        yaxis_title="Northing",
        legend=dict(orientation="h")
    )
    # lock aspect ratio so X and Y scale equally like CAD
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def build_3d_orbit_view(df):
    """
    3D orbit/zoom view using Plotly scatter3d.
    """
    if df is None or df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=df["Easting"],
        y=df["Northing"],
        z=df["Elevation"],
        mode="markers+text",
        text=df["Name"],
        textposition="top center",
        marker=dict(size=4),
        name="Design Points"
    ))

    fig.update_layout(
        title="3D Orbit View (Design Points)",
        scene=dict(
            xaxis_title="Easting",
            yaxis_title="Northing",
            zaxis_title="Elevation",
            aspectmode="data",
        )
    )
    return fig


# -----------------------------------------------------------------------------
# UI Pages
# -----------------------------------------------------------------------------


def page_home():
    st.title("Piling QA Dashboard")

    st.write(
        "Upload your design data and (later) as-built data. "
        "Once loaded, you'll be able to view design points in 2D and 3D."
    )

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("1. Upload Design Model")
        st.caption("Accepted: LandXML (.xml), DXF (.dxf), Leica Project (.lok)")
        design_file = st.file_uploader(
            "Design Data",
            type=["xml", "dxf", "lok"],
            key="design_upload",
            help="Your planned pile / drill point coordinates."
        )

        st.subheader("2. Upload As-Built CSV (Optional for future steps)")
        st.caption("We'll wire this into analysis later.")
        st.file_uploader(
            "As-Built Data (.csv)",
            type=["csv"],
            key="asbuilt_upload",
            help="Machine log / survey log from rig"
        )

        # If user provided a design file, parse it and store it
        if design_file is not None:
            df = load_design_file(design_file)
            if df is not None and not df.empty:
                st.session_state["design_points_df"] = df
                st.success("Design data loaded.")
                st.write(df.head())

                # Button to jump to overview
                if st.button("Go to Overview ▶"):
                    st.session_state["page"] = "overview"

    with col_right:
        st.image("rig_image.jpg", caption="Piling Rig", use_column_width=True)


def page_overview():
    st.title("Overview: Design Points")

    df = st.session_state.get("design_points_df", None)

    if df is None or df.empty:
        st.warning("No design data loaded yet. Go back to Home and upload a design file.")
        if st.button("⬅ Back to Home"):
            st.session_state["page"] = "home"
        return

    # Sidebar controls
    with st.sidebar:
        st.header("View Controls")
        view_mode = st.radio(
            "View mode",
            ["Local 2D Plan", "3D Orbit"],
            index=0
        )

        st.markdown("**Design Points Loaded:**")
        st.write(len(df))

        if st.button("⬅ Back to Home"):
            st.session_state["page"] = "home"

    # Main view
    if view_mode == "Local 2D Plan":
        fig2d = build_local_plan_view(df)
        st.plotly_chart(fig2d, use_container_width=True)

    elif view_mode == "3D Orbit":
        fig3d = build_3d_orbit_view(df)
        st.plotly_chart(fig3d, use_container_width=True)

    # Show raw data table for reference
    st.subheader("Design Points Data")
    st.dataframe(df)


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------

if st.session_state["page"] == "home":
    page_home()
elif st.session_state["page"] == "overview":
    page_overview()
else:
    st.session_state["page"] = "home"
    page_home()
