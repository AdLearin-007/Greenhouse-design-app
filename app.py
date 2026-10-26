"""
Greenhouse System Planner - website (Streamlit + Plotly).

Run it:
    pip install -r requirements.txt
    streamlit run app.py
Then open the address it prints (usually http://localhost:8501).
"""
import plotly.graph_objects as go
import streamlit as st

from planner import (GLAZING, HYDRO_METHODS, INFO, STYLES, SYSTEMS, WATER_LOOPS,
                     Settings, balance_note, build)

st.set_page_config(page_title="Greenhouse System Planner", page_icon="🌱", layout="wide")

# Draw order and look of each component in the 3D view
OPACITY = {"water": 0.7, "shade": 0.55, "door": 0.45}
FLAT = {"glazing", "shade"}  # no lighting on see-through surfaces


# --------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Build your greenhouse")
    style = st.radio("Structure style", list(STYLES), format_func=STYLES.get, index=2)
    system = st.radio("Growing system", list(SYSTEMS), format_func=SYSTEMS.get, index=2)
    hydro = "nft"
    if system == "hydro":
        hydro = st.radio("Hydroponic method", list(HYDRO_METHODS), format_func=HYDRO_METHODS.get)
    width = st.slider("Width (span), m", 4.0, 16.0, 9.0, 0.5)
    length = st.slider("Length, m", 8, 32, 18, 1)
    glazing = st.radio("Glazing", list(GLAZING), format_func=lambda k: GLAZING[k][0], index=1)
    st.subheader("Equipment & view")
    lights = st.checkbox("Grow lights", True)
    fans = st.checkbox("Exhaust fans", True)
    shade = st.checkbox("Shade cloth", False)
    flow = st.checkbox("Show water flow", True)
    hide_glazing = st.checkbox("Hide glazing (see inside)", False)
    view = st.radio("Camera", ["Orbit", "Plan (top-down)", "Door end"], horizontal=True)

settings = Settings(style=style, system=system, hydro=hydro, width=width, length=float(length),
                    glazing=glazing, lights=lights, fans=fans, shade=shade, flow=flow,
                    hide_glazing=hide_glazing or view.startswith("Plan"))


@st.cache_data(show_spinner="Building the greenhouse...")
def cached_build(s: Settings):
    return build(s)


model = cached_build(settings)
stats = model.stats


# --------------------------------------------------------------------------
# 3D figure
# --------------------------------------------------------------------------
def name_of(key):
    if key == "glazing":
        return GLAZING[settings.glazing][0]
    return INFO[key][0]


def make_figure(m, s: Settings) -> go.Figure:
    fig = go.Figure()
    shown = set()

    def legend(key):
        first = key not in shown
        shown.add(key)
        return dict(name=name_of(key), legendgroup=key, showlegend=first)

    w, L = s.width, s.length
    # ground
    fig.add_trace(go.Mesh3d(x=[-w * 2, w * 2, w * 2, -w * 2], y=[-L, -L, L, L], z=[-.01] * 4,
                            i=[0, 0], j=[1, 2], k=[2, 3], color="#AEBF9E", hoverinfo="skip",
                            showlegend=False, flatshading=True))

    for key, mesh in m.meshes.items():
        if key == "glazing":
            if s.hide_glazing:
                continue
            color, opacity = m.glazing_color, m.glazing_opacity
        else:
            color, opacity = INFO[key][2], OPACITY.get(key, 1.0)
        light = (dict(ambient=1, diffuse=0, specular=0) if key in FLAT
                 else dict(ambient=.55, diffuse=.8, specular=.15, roughness=.6))
        fig.add_trace(go.Mesh3d(
            x=mesh.x, y=mesh.y, z=mesh.z, i=mesh.i, j=mesh.j, k=mesh.k,
            color=color, opacity=opacity, flatshading=True, lighting=light,
            lightposition=dict(x=2000, y=1500, z=4000),
            hovertemplate=f"<b>{name_of(key)}</b><extra></extra>", **legend(key)))

    for key, (xs, ys, zs, width) in m.lines.items():
        color = "#5B6870" if key == "frame" else INFO[key][2]
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=color, width=width),
                                   hovertemplate=f"<b>{name_of(key)}</b><extra></extra>", **legend(key)))

    for key, (xs, ys, zs, cs, ss) in m.points.items():
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="markers",
                                   marker=dict(color=cs, size=ss, line=dict(width=0)),
                                   hovertemplate=f"<b>{name_of(key)}</b><extra></extra>", **legend(key)))

    if s.flow and m.flow_paths:
        # A bright line over each loop, plus arrowheads (cones) pointing downstream
        fx, fy, fz, cx, cy, cz, cu, cv, cw = ([] for _ in range(9))
        for path in m.flow_paths:
            for p in path:
                fx.append(p[0]); fy.append(p[1]); fz.append(p[2] + .03)
            fx.append(None); fy.append(None); fz.append(None)
            for a, b in zip(path, path[1:]):
                d = [b[i] - a[i] for i in range(3)]
                n = sum(v * v for v in d) ** .5
                if n < .3:
                    continue
                steps = max(1, int(n // 2.5))
                for t in range(steps):
                    f = (t + .5) / steps
                    cx.append(a[0] + d[0] * f); cy.append(a[1] + d[1] * f); cz.append(a[2] + d[2] * f + .03)
                    cu.append(d[0] / n); cv.append(d[1] / n); cw.append(d[2] / n)
        fig.add_trace(go.Scatter3d(x=fx, y=fy, z=fz, mode="lines", line=dict(color=INFO["flow"][2], width=7),
                                   hovertemplate="<b>Water flow</b><extra></extra>", **legend("flow")))
        fig.add_trace(go.Cone(x=cx, y=cy, z=cz, u=cu, v=cv, w=cw, sizemode="absolute", sizeref=.35,
                              anchor="center", colorscale=[[0, INFO["flow"][2]], [1, INFO["flow"][2]]],
                              showscale=False, hoverinfo="skip", legendgroup="flow", showlegend=False))

    span = max(w, L)
    cameras = {
        "Orbit": dict(eye=dict(x=1.1, y=1.35, z=.75), up=dict(x=0, y=0, z=1)),
        "Plan (top-down)": dict(eye=dict(x=0, y=0, z=1.9), up=dict(x=0, y=1, z=0)),
        "Door end": dict(eye=dict(x=0, y=1.25, z=.3), up=dict(x=0, y=0, z=1)),
    }
    axis = dict(visible=False, showbackground=False)
    fig.update_layout(
        height=720, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(xaxis=dict(axis, range=[-span * .75, span * .75]),
                   yaxis=dict(axis, range=[-span * .75, span * .75]),
                   zaxis=dict(axis, range=[-.05, span * .5]),
                   aspectmode="manual", aspectratio=dict(x=1, y=1, z=.67),
                   camera=cameras[view], dragmode="orbit"),
        legend=dict(title="Components (click to hide)", itemsizing="constant",
                    bgcolor="rgba(255,255,255,.75)", x=0, y=1),
        uirevision=view,  # keep your camera angle while you change settings
    )
    return fig


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
method = settings.method
title_bits = [STYLES[style], SYSTEMS[system] if system != "hydro" else f"Hydroponic - {HYDRO_METHODS[hydro]}"]
st.title("Greenhouse System Planner")
st.caption(f"{' · '.join(title_bits)} · {width:g} m × {length} m · {GLAZING[glazing][0]}")

st.plotly_chart(make_figure(model, settings), use_container_width=True,
                config={"displaylogo": False, "scrollZoom": True})
st.caption("Drag to orbit, scroll to zoom, hover any part for its name. Click legend items to hide them.")

st.subheader("Layout numbers")
cards = [
    ("Footprint", f"{stats['footprint']:,.0f} m²"),
    ("Air volume", f"{stats['volume']:,.0f} m³"),
    ("Growing area", f"{stats['grow_area']:,.1f} m²"),
    ("Plant sites", f"{stats['plant_sites']:,}"),
    ("Light through cover", f"{stats['light_pct']}%"),
    ("Glazing area", f"{stats['glazing_area']:,.0f} m²"),
    ("Exhaust needed", f"{stats['volume']:,.0f} m³/min"),
    ("36-inch fans", f"{stats['fans_needed']}" + (f" ({stats['fans_placed']} fit)" if fans and stats['fans_placed'] < stats['fans_needed'] else "")),
]
if method == "trad":
    cards += [("Soil volume", f"{stats['soil_m3']:,.1f} m³"), ("Storage tank", f"{stats['water_l']:,.0f} L")]
else:
    cards += [("Water in system", f"{stats['water_l']:,.0f} L"), ("Rows", f"{stats['rows']}")]
if method == "aqua":
    cards += [("Fish capacity", f"{stats['fish_capacity_kg']:,.0f} kg"), ("Feed for beds", f"{stats['feed_g_day']:,.0f} g/day")]
for row in range(0, len(cards), 4):
    cols = st.columns(4)
    for col, (label, value) in zip(cols, cards[row:row + 4]):
        col.metric(label, value)
st.info(balance_note(stats, method))

left, right = st.columns(2)
with left:
    st.subheader("Water loop")
    st.markdown("\n".join(f"{n}. **{a}** - {b}" for n, (a, b) in enumerate(WATER_LOOPS[method], 1)))
with right:
    st.subheader("Components")
    keys = list(dict.fromkeys(list(model.meshes) + list(model.lines) + list(model.points)))
    for key in keys:
        if key in ("water", "soil", "rafts", "fish"):
            continue
        desc = GLAZING[glazing][4] if key == "glazing" else INFO[key][1]
        with st.expander(name_of(key)):
            st.write(desc)
