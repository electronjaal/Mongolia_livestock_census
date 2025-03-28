import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static

##################################
# 1) Strings for English & Mongolian
##################################
strings = {
    "en": {
        "app_title": "Livestock Census of Mongolia",
        "sidebar_header": "Livestock Census Filters",
        "language_selector": "Language",
        "select_year": "Select Year",
        "national_totals_for": "National Totals for",
        "total_livestock": "Total Livestock",
        "select_livestock_type": "Select Livestock Type",
        "geographic_level": "Geographic Level",
        "aimags_label": "Aimags",
        "soums_label": "Soums",
        "heatmap_header": "Livestock Heatmap",
        "livestock_count": "Livestock Count",
        "tooltip_aimag": "Aimag:",
        "tooltip_soum": "Soum:",
        "tooltip_type": "Livestock Type:",
        "tooltip_count": "Livestock Count:",
        "total_keyword": "Total"      # matches data in SCR_ENG1
    },
    "mn": {
        "app_title": "Монголын мал тооллогын өгөгдлийн орон зайн дүрслэл",
        "sidebar_header": "Мал тооллогын шүүлтүүр",
        "language_selector": "Хэл",
        "select_year": "Он сонгох",
        "national_totals_for": "Тухайн оны нэгдсэн дүн",
        "total_livestock": "Нийт мал",
        "select_livestock_type": "Малын төрөл сонгох",
        "geographic_level": "Засаг захиргааны нэгж",
        "aimags_label": "Аймаг",
        "soums_label": "Сум",
        "heatmap_header": "Малын тоо газрын зураг дээр",
        "livestock_count": "Малын тоо",
        "tooltip_aimag": "Аймаг:",
        "tooltip_soum": "Сум:",
        "tooltip_type": "Малын төрөл:",
        "tooltip_count": "Малын тоо:",
        "total_keyword": "Бүгд"       # matches data in SCR_MN1
    }
}

##################################
# 2) Page Config
##################################
st.set_page_config(
    page_title="Livestock Census",
    layout="wide",
    initial_sidebar_state="expanded"
)

##################################
# 3) Language Selection in Sidebar
#    Default language is Mongolian
##################################
lang_choice = st.sidebar.radio(
    label=strings["mn"]["language_selector"] + " / " + strings["en"]["language_selector"], 
    options=["Монгол", "English"],
    index=0  # Mongolian as default
)
lang = "mn" if lang_choice == "Монгол" else "en"

##################################
# 4) Data Loading
##################################
@st.cache_data
def load_data():
    df = pd.read_csv('mal_toollogo_buh_on.tsv', sep='\t')
    df['DTVAL_CO'] = df['DTVAL_CO'] * 1000
    aimags = gpd.read_file('aimags.json')
    soums = gpd.read_file('soums.json')
    return df, aimags, soums

data, aimags, soums = load_data()

##################################
# 5) Determine which columns to use for livestock type
##################################
if lang == "mn":
    livestock_col = "SCR_MN1"
    total_key = strings["mn"]["total_keyword"]   # 'Бүгд'
else:
    livestock_col = "SCR_ENG1"
    total_key = strings["en"]["total_keyword"]   # 'Total'

region_aimag_code = "NAME_1"  
region_soum_code = "NAME_2"

##################################
# 6) Sidebar Filters
##################################
st.sidebar.header(strings[lang]["sidebar_header"])

selected_period = st.sidebar.selectbox(
    strings[lang]["select_year"],
    sorted(data["Period"].unique(), reverse=True)
)

############################
# Sort Animal Types by CODE1
############################
# 1) Subset rows that have CODE1 + the livestock col
valid_animals = data.dropna(subset=["CODE1", livestock_col]).copy()

# 2) Convert CODE1 to integer to handle leading zeros
def safe_int(x):
    try:
        return int(x)
    except:
        return 999999  # fallback if parse fails

valid_animals["CODE1_int"] = valid_animals["CODE1"].apply(safe_int)

# 3) Keep only distinct pairs of (CODE1_int, livestock_col)
valid_animals = valid_animals[["CODE1_int", livestock_col]].drop_duplicates()

# 4) Sort by CODE1_int ascending
valid_animals.sort_values("CODE1_int", inplace=True)

# 5) Build final list in numeric order, removing duplicates
final_order = []
seen = set()
for _, row in valid_animals.iterrows():
    t = row[livestock_col]
    if t not in seen:
        seen.add(t)
        final_order.append(t)

# 6) Find index of total_key for default selection
default_index = 0
if total_key in final_order:
    default_index = final_order.index(total_key)

# 7) Livestock selectbox
selected_animal = st.sidebar.selectbox(
    strings[lang]["select_livestock_type"],
    final_order,
    index=default_index
)

# 8) Geographic level
level_choice = st.sidebar.radio(
    strings[lang]["geographic_level"],
    [strings[lang]["aimags_label"], strings[lang]["soums_label"]]
)

##############################
# Sidebar: national totals
##############################
summary_data = data[(data["Period"] == selected_period) & (data["CODE"] == 0)]
st.sidebar.write(f"**{strings[lang]['national_totals_for']} {selected_period}:**")
for _, row in summary_data.iterrows():
    row_type_name = row[livestock_col] if pd.notna(row[livestock_col]) else ""
    if row_type_name == total_key:
        st.sidebar.subheader(
            f"{strings[lang]['total_livestock']}: {row['DTVAL_CO']:,.0f}"
        )
    else:
        st.sidebar.write(
            f"{row_type_name}: {row['DTVAL_CO']:,.0f}"
        )

##################################
# 7) Main Page Title
##################################
st.title(strings[lang]["app_title"])

##################################
# 8) Filter data for the chosen period & livestock
##################################
filtered_data = data[
    (data["Period"] == selected_period) &
    (data[livestock_col] == selected_animal)
].copy()

##################################
# 9) Determine region DataFrame & merges
##################################
if level_choice == strings[lang]["aimags_label"]:
    geo_df = aimags.copy()
    geo_df['Region'] = geo_df[region_aimag_code]
    filtered_data = filtered_data[(filtered_data['CODE'] >= 100) & (filtered_data['CODE'] < 1000)]
    region_alias = strings[lang]["tooltip_aimag"]
    merged = geo_df.merge(
        filtered_data,
        left_on=region_aimag_code,
        right_on='SCR_ENG',
        how='left'
    )
else:
    geo_df = soums.copy()
    geo_df['Region'] = geo_df[region_soum_code]
    filtered_data = filtered_data[(filtered_data['CODE'] >= 1000) & (filtered_data['CODE'] < 100000)]
    region_alias = strings[lang]["tooltip_soum"]
    merged = geo_df.merge(
        filtered_data,
        left_on=region_soum_code,
        right_on='SCR_ENG',
        how='left'
    )

##################################
# 10) Display Interactive Map
##################################
st.header(f"{strings[lang]['heatmap_header']} ({selected_animal}, {selected_period})")

m = folium.Map(location=[46.8625, 103.8467], zoom_start=6)

folium.Choropleth(
    geo_data=merged,
    data=merged,
    columns=["Region", "DTVAL_CO"],
    key_on='feature.properties.Region',
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name=strings[lang]["livestock_count"],
    nan_fill_color="white",
).add_to(m)

folium.GeoJson(
    merged,
    tooltip=folium.GeoJsonTooltip(
        fields=["Region", livestock_col, "DTVAL_CO"],
        aliases=[
            region_alias,
            strings[lang]["tooltip_type"],
            strings[lang]["tooltip_count"]
        ],
        localize=True,
        labels=True,
        sticky=True
    )
).add_to(m)

folium_static(m, width=None, height=600)
