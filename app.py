from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA = Path(__file__).parent / "data"
TABLES = DATA / "summary_tables"

PUBLIC_COLOR = "#2F6FDE"
PRIVATE_COLOR = "#E08A1E"
LINE_COLOR = "#2F6FDE"
ACCENT_COLOR = "#C0392B"

st.set_page_config(page_title="Preschool Registration in Barcelona", layout="wide")


@st.cache_data
def load_data():
    births = pd.read_csv(DATA / "births_bcn.csv").sort_values("Year")
    vs = pd.read_csv(TABLES / "places_vs_children.csv").sort_values("School Term")
    by_type = pd.read_csv(TABLES / "places_offer_by_school_type.csv").sort_values("School Year")
    id_cols = ["Municipal District", "Type of School", "Type Enrollment"]
    frames = []
    for name in ["places_offer_by_year.csv", "places_enrolled_by_year.csv"]:
        wide = pd.read_csv(TABLES / name)
        frames.append(wide.melt(id_vars=id_cols, var_name="School Year", value_name="Places"))
    districts = pd.concat(frames, ignore_index=True)
    schools = pd.read_csv(DATA / "schools_teachers_bcn.csv").sort_values("Curs")
    centres = pd.read_csv(DATA / "places_offer_p3_bcn.csv")
    return births, vs, by_type, districts, schools, centres


births, vs, by_type, districts, schools, centres = load_data()

st.title("Preschool Registration in Barcelona")
st.write(
    "Are there enough P3 places for the children who need one, and does the public "
    "and private mix depend on the district? Data from Idescat and Dades Obertes de Catalunya."
)

# Key numbers
peak = births.loc[births["Total"].idxmax()]
last = births.iloc[-1]
births_change = (last["Total"] / peak["Total"] - 1) * 100

vs_latest = vs.iloc[-1]
vs_first = vs.iloc[0]
places_change = (vs_latest["# Places"] / vs_first["# Places"] - 1) * 100
gap = int(vs_latest["# Places"] - vs_latest["# Children"])

k1, k2, k3 = st.columns(3)
k1.metric(
    f"Births, {int(last['Year'])} vs {int(peak['Year'])} peak",
    f"{int(last['Total']):,}",
    f"{births_change:.1f}%",
)
k2.metric(
    f"P3 places, {vs_latest['School Term']} vs {vs_first['School Term']}",
    f"{int(vs_latest['# Places']):,}",
    f"{places_change:.1f}%",
)
k3.metric(
    f"Places minus children, {vs_latest['School Term']}",
    f"{gap:,}",
    "fewer places than children" if gap < 0 else "more places than children",
    delta_color="inverse" if gap < 0 else "normal",
)

tab1, tab2, tab3 = st.tabs(["Births", "Places vs children", "Public vs private"])

with tab1:
    years = births["Year"].astype(int)
    lo, hi = st.slider(
        "Year range",
        int(years.min()),
        int(years.max()),
        (int(years.min()), int(years.max())),
    )
    view = births[(births["Year"] >= lo) & (births["Year"] <= hi)]
    fig = px.line(view, x="Year", y="Total", markers=True, labels={"Total": "Births"})
    fig.update_traces(line_color=LINE_COLOR)
    fig.update_layout(margin=dict(t=20), yaxis_title="Births in Barcelona")
    st.plotly_chart(fig, width="stretch")
    with st.expander("Boys and girls"):
        split = view.melt(id_vars="Year", value_vars=["Boys", "Girls"], var_name="Sex", value_name="Births")
        st.plotly_chart(px.bar(split, x="Year", y="Births", color="Sex", barmode="group"), width="stretch")

with tab2:
    long = vs.melt(id_vars="School Term", value_vars=["# Places", "# Children"], var_name="Series", value_name="Count")
    long["Series"] = long["Series"].str.replace("# ", "", regex=False)
    fig = px.line(
        long,
        x="School Term",
        y="Count",
        color="Series",
        markers=True,
        color_discrete_map={"Places": LINE_COLOR, "Children": ACCENT_COLOR},
    )
    fig.update_layout(margin=dict(t=20), xaxis_title=None, yaxis_title="P3 places and children")
    st.plotly_chart(fig, width="stretch")

    gap_df = vs.assign(Gap=vs["# Places"] - vs["# Children"])
    fig_gap = px.bar(
        gap_df,
        x="School Term",
        y="Gap",
        labels={"Gap": "Places minus children"},
        title="Places minus children (negative means fewer places than children)",
    )
    fig_gap.update_traces(marker_color=[ACCENT_COLOR if g < 0 else LINE_COLOR for g in gap_df["Gap"]])
    fig_gap.update_layout(xaxis_title=None)
    st.plotly_chart(fig_gap, width="stretch")

with tab3:
    st.subheader("P3 places offered, public vs private")
    st.caption("Private includes concertada schools.")
    long = by_type.melt(
        id_vars="School Year", value_vars=["Public", "Private"], var_name="Type of School", value_name="Places"
    )
    fig = px.bar(
        long,
        x="School Year",
        y="Places",
        color="Type of School",
        barmode="group",
        color_discrete_map={"Public": PUBLIC_COLOR, "Private": PRIVATE_COLOR},
    )
    fig.update_layout(xaxis_title=None, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Number of schools, public vs private")
    st.caption("Private includes concertada schools. City-wide figures, not split by district.")
    sch = schools.melt(
        id_vars="Curs",
        value_vars=["Centres_Públics", "Centres_Privats"],
        var_name="Type of School",
        value_name="Schools",
    )
    sch["Type of School"] = sch["Type of School"].map({"Centres_Públics": "Public", "Centres_Privats": "Private"})
    fig = px.bar(
        sch,
        x="Curs",
        y="Schools",
        color="Type of School",
        barmode="group",
        color_discrete_map={"Public": PUBLIC_COLOR, "Private": PRIVATE_COLOR},
        labels={"Curs": "School year"},
    )
    fig.update_layout(xaxis_title=None, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    st.subheader("By district")
    c1, c2, c3 = st.columns(3)
    measure = c1.selectbox("Measure", sorted(districts["Type Enrollment"].unique()))
    school_years = sorted(districts["School Year"].unique())
    year = c2.selectbox("School year", school_years, index=len(school_years) - 1)
    pool = districts[(districts["Type Enrollment"] == measure) & (districts["School Year"] == year)]
    district_names = sorted(pool["Municipal District"].unique())
    chosen = c3.selectbox("District", ["All districts"] + district_names)

    pivot = pool.pivot_table(index="Municipal District", columns="Type of School", values="Places", aggfunc="sum").fillna(0)
    for col in ["Public", "Private"]:
        if col not in pivot.columns:
            pivot[col] = 0
    total = pivot["Public"] + pivot["Private"]
    pivot["Public %"] = pivot["Public"] / total * 100
    pivot["Private %"] = pivot["Private"] / total * 100
    pivot = pivot.sort_values("Public %")

    share = pivot.reset_index().melt(
        id_vars="Municipal District",
        value_vars=["Public %", "Private %"],
        var_name="Type of School",
        value_name="Share",
    )
    share["Type of School"] = share["Type of School"].str.replace(" %", "", regex=False)
    share["Label"] = share["Share"].round(0).astype(int).astype(str) + "%"
    fig = px.bar(
        share,
        x="Share",
        y="Municipal District",
        color="Type of School",
        orientation="h",
        text="Label",
        category_orders={"Municipal District": list(pivot.index), "Type of School": ["Public", "Private"]},
        color_discrete_map={"Public": PUBLIC_COLOR, "Private": PRIVATE_COLOR},
        labels={"Share": "Share of places (%)"},
        title=f"Public and private share of places by district, {year}",
    )
    fig.update_layout(yaxis_title=None, xaxis_range=[0, 100], height=max(400, 32 * len(pivot) + 120))
    fig.update_traces(textposition="inside")
    if chosen != "All districts":
        fig.update_yaxes(ticktext=[("> " + d + " <") if d == chosen else d for d in pivot.index], tickvals=list(pivot.index))
    st.plotly_chart(fig, width="stretch")

    st.markdown("**Schools offering P3 by district**")
    needed = {"Curs", "Codi centre", "Nom naturalesa", "Nom DM", "Nom ensenyament"}
    if not needed.issubset(centres.columns):
        st.info("School counts by district are not available for this dataset.")
    else:
        cen = centres[centres["Nom ensenyament"].astype(str).str.contains("Parvulari", case=False, na=False)]
        cen = cen[cen["Curs"].astype(str) == str(year)].copy()
        if cen.empty:
            st.info(f"No school-level data for {year}.")
        else:
            cen["Type of School"] = cen["Nom naturalesa"].astype(str).str.startswith("Púb").map(
                {True: "Public", False: "Private"}
            )
            count = (
                cen.groupby(["Nom DM", "Type of School"])["Codi centre"].nunique().reset_index(name="Schools")
            )
            order = (
                count.groupby("Nom DM")["Schools"].sum().sort_values().index.tolist()
            )
            fig = px.bar(
                count,
                x="Schools",
                y="Nom DM",
                color="Type of School",
                orientation="h",
                barmode="stack",
                category_orders={"Nom DM": order, "Type of School": ["Public", "Private"]},
                color_discrete_map={"Public": PUBLIC_COLOR, "Private": PRIVATE_COLOR},
                title=f"Schools offering P3 by district, {year} (private includes concertada)",
            )
            fig.update_layout(yaxis_title=None, height=max(400, 32 * len(order) + 120))
            st.plotly_chart(fig, width="stretch")

    if chosen != "All districts":
        history = districts[
            (districts["Type Enrollment"] == measure) & (districts["Municipal District"] == chosen)
        ]
        fig = px.bar(
            history,
            x="School Year",
            y="Places",
            color="Type of School",
            barmode="group",
            title=f"{chosen}: {measure.lower()} over time",
            color_discrete_map={"Public": PUBLIC_COLOR, "Private": PRIVATE_COLOR},
        )
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(fig, width="stretch")

st.caption("Source: Idescat and Dades Obertes de Catalunya. Analysis by Rita Pereira.")
