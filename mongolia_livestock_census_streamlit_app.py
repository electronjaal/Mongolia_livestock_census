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
        "app_title": "Монголын мал тооллого",
        "sidebar_header": "Мал тооллогын шүүлтүүр",
        "language_selector": "Хэл",
        "select_year": "Он сонгох",
        "national_totals_for": "Тухайн оны нэгдсэн дүн",
        "total_livestock": "Нийт мал",
        "select_livestock_type": "Малын төрөл сонгох",
        "geographic_level": "Нутаг дэвсгэрийн түвшин",
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
##################################
lang_choice = st.sidebar.radio(
    label=strings["en"]["language_selector"] + " / " + strings["mn"]["language_selector"],
    options=["English", "Монгол"],
    index=0
)
lang = "en" if lang_choice == "English" else "mn"

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
    livestock_col = "SCR_MN1"     # Mongolian
    region_aimag_code = "NAME_1"  # unchanged, we still match region by English name
    region_soum_code = "NAME_2"
    total_key = strings["mn"]["total_keyword"]  # 'Бүгд'
else:
    livestock_col = "SCR_ENG1"    # English
    region_aimag_code = "NAME_1"  # unchanged, we still match region by English name
    region_soum_code = "NAME_2"
    total_key = strings["en"]["total_keyword"]  # 'Total'

##################################
# 6) Sidebar Filters
##################################
st.sidebar.header(strings[lang]["sidebar_header"])

selected_period = st.sidebar.selectbox(
    strings[lang]["select_year"],
    sorted(data["Period"].unique(), reverse=True)
)

# 6.2) Collect livestock types from appropriate column
all_types = list(data[livestock_col].dropna().unique())
selected_animal = st.sidebar.selectbox(strings[lang]["select_livestock_type"], sorted(all_types))

# 6.3) Geographic level
level_choice = st.sidebar.radio(
    strings[lang]["geographic_level"],
    [strings[lang]["aimags_label"], strings[lang]["soums_label"]]
)

# 6.1) National totals (CODE=0) for the selected year
summary_data = data[(data["Period"] == selected_period) & (data["CODE"] == 0)]
st.sidebar.write(f"**{strings[lang]['national_totals_for']} {selected_period}:**")

for _, row in summary_data.iterrows():
    # We compare the row's *Mongolian or English column* to the total keyword
    # But note: row might only have 'SCR_ENG1' or 'SCR_MN1'.
    # If your data for CODE=0 also has both SCR_ENG1 and SCR_MN1, we can do row[livestock_col].
    # If not, we might do a separate approach. We'll assume both columns are present.
    row_type_name = row[livestock_col] if pd.notna(row[livestock_col]) else ""
    
    if row_type_name == total_key:
        st.sidebar.subheader(
            f"{strings[lang]['total_livestock']}: {row['DTVAL_CO']:,.0f}"
        )
    else:
        # e.g., Horse / Адуу, Cattle / Үхэр, etc.
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
    # Aimags: CODE < 1000
    filtered_data = filtered_data[(filtered_data['CODE'] >= 100) & (filtered_data['CODE'] < 1000)]
    merged = geo_df.merge(filtered_data, left_on=region_aimag_code, right_on='SCR_ENG', how='left')
    region_alias = strings[lang]["tooltip_aimag"]
else:
    geo_df = soums.copy()
    geo_df['Region'] = geo_df[region_soum_code]
    # Soums: 1000 <= CODE < 100000
    filtered_data = filtered_data[(filtered_data['CODE'] >= 1000) & (filtered_data['CODE'] < 100000)]
    merged = geo_df.merge(filtered_data, left_on=region_soum_code, right_on='SCR_ENG', how='left')
    region_alias = strings[lang]["tooltip_soum"]

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

# In the tooltip, we display the chosen livestock column
# along with the region and DTVAL_CO
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
