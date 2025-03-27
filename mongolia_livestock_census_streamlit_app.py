import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static

# Load datasets
@st.cache_data
def load_data():
    df = pd.read_csv('mal_toollogo_buh_on.tsv', sep='\t')
    df['DTVAL_CO'] = df['DTVAL_CO'] * 1000
    
    aimags = gpd.read_file('aimags.json')
    soums = gpd.read_file('soums.json')
    
    return df, aimags, soums

data, aimags, soums = load_data()

# Sidebar interaction
st.sidebar.header("Animal Count Filters")
selected_period = st.sidebar.selectbox("Select Year", sorted(data["Period"].unique(), reverse=True))
animal_types = ['Total'] + list(data["SCR_ENG1"].unique())
selected_animal = st.sidebar.selectbox("Select Animal", animal_types)
level = st.sidebar.radio("Geographic Level", ["Aimags", "Soums"])

# Filter data based on user selection and CODE condition
filtered_data = data[(data["Period"] == selected_period)]
if selected_animal != 'Total':
    filtered_data = filtered_data[filtered_data["SCR_ENG1"] == selected_animal]
else:
    filtered_data = filtered_data[filtered_data["SCR_ENG1"] == 'Total']

# Selecting GeoDataFrame and merge keys clearly
if level == "Aimags":
    geo_df = aimags.copy()
    geo_df['Region'] = geo_df['NAME_1']
    filtered_data = filtered_data[filtered_data['CODE'] < 1000]
    merged = geo_df.merge(filtered_data, left_on='NAME_1', right_on='SCR_ENG', how='left')
else:
    geo_df = soums.copy()
    geo_df['Region'] = geo_df['NAME_2']
    filtered_data = filtered_data[(filtered_data['CODE'] >= 1000) & (filtered_data['CODE'] < 100000)]
    merged = geo_df.merge(filtered_data, left_on='NAME_2', right_on='SCR_ENG', how='left')

# Display interactive map
st.header(f"Animal Count Heatmap ({selected_animal}, {selected_period}, {level})")
m = folium.Map(location=[46.8625, 103.8467], zoom_start=6)

# Generate choropleth heatmap
folium.Choropleth(
    geo_data=merged,
    data=merged,
    columns=["Region", "DTVAL_CO"],
    key_on='feature.properties.Region',
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Animal Count",
    nan_fill_color="white",
).add_to(m)

# Clear and informative tooltip
folium.GeoJson(
    merged,
    tooltip=folium.GeoJsonTooltip(
        fields=["Region", "SCR_ENG1", "DTVAL_CO"],
        aliases=[f"{level}: ", "Animal Type: ", "Animal Count: "],
        localize=True,
        labels=True,
        sticky=True
    )
).add_to(m)

# Render your map
folium_static(m, width=900, height=600)
