import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static

@st.cache_data
def load_data():
    df = pd.read_csv('mal_toollogo_buh_on.tsv', sep='\t')
    # Multiply DTVAL_CO by 1000
    df['DTVAL_CO'] = df['DTVAL_CO'] * 1000
    
    aimags = gpd.read_file('aimags.json')
    soums = gpd.read_file('soums.json')
    return df, aimags, soums

# Load datasets once
data, aimags, soums = load_data()

################################
# Sidebar: filters + national totals
################################

st.sidebar.header("Livestock Census Filters")
selected_period = st.sidebar.selectbox(
    "Select Year",
    sorted(data["Period"].unique(), reverse=True)
)

# Continue with the rest of the filters
animal_types = list(data["SCR_ENG1"].unique())
selected_animal = st.sidebar.selectbox("Select Livestock Type", animal_types)
level = st.sidebar.radio("Geographic Level", ["Aimags", "Soums"])


# Show national totals in the sidebar
summary_data = data[
    (data["Period"] == selected_period) 
    & (data['CODE'] == 0)  # CODE=0 is the national total row
].copy()

st.sidebar.write(f"**National Totals for {selected_period}:**")
for i, row in summary_data.iterrows():
    if row['SCR_ENG1'] == 'Total':
        st.sidebar.subheader(
            f"Total Livestock: {row['DTVAL_CO']:,.0f}"
        )
    else:
        st.sidebar.write(
            f"Total {row['SCR_ENG1']}: {row['DTVAL_CO']:,.0f}"
        )

################################
# Main screen
################################

st.title("Livestock Census of Mongolia")

# Filter data for mapping
filtered_data = data[
    (data["Period"] == selected_period) 
    & (data["SCR_ENG1"] == selected_animal)
].copy()

if level == "Aimags":
    geo_df = aimags.copy()
    geo_df['Region'] = geo_df['NAME_1']
    # Aimag have CODE < 1000
    filtered_data = filtered_data[(filtered_data['CODE'] >= 100) & (filtered_data['CODE'] < 1000)]
    merged = geo_df.merge(
        filtered_data, left_on='NAME_1', right_on='SCR_ENG', how='left'
    )
else:
    geo_df = soums.copy()
    geo_df['Region'] = geo_df['NAME_2']
    # Soum have 1000 <= CODE < 100000
    filtered_data = filtered_data[
        (filtered_data['CODE'] >= 1000) & (filtered_data['CODE'] < 100000)
    ]
    merged = geo_df.merge(
        filtered_data, left_on='NAME_2', right_on='SCR_ENG', how='left'
    )

# Create interactive map
st.header(f"Livestock Heatmap ({selected_animal}, {selected_period}, {level})")
m = folium.Map(location=[46.8625, 103.8467], zoom_start=6)

# Choropleth layer
folium.Choropleth(
    geo_data=merged,
    data=merged,
    columns=["Region", "DTVAL_CO"],
    key_on='feature.properties.Region',
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Livestock Count",
    nan_fill_color="white",
).add_to(m)

# Tooltip with region + livestock info
folium.GeoJson(
    merged,
    tooltip=folium.GeoJsonTooltip(
        fields=["Region", "SCR_ENG1", "DTVAL_CO"],
        aliases=[f"{level}:", "Livestock Type:", "Livestock Count:"],
        localize=True,
        labels=True,
        sticky=True
    )
).add_to(m)

# Display map
folium_static(m, width=1100, height=600)
