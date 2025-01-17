import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import math
from datetime import datetime

# -----------------------
# 1. PAGE CONFIG & SETUP
# -----------------------
st.set_page_config(
    layout="wide",
    page_title="Viator North America Visualization",
    page_icon="🗺️"
)

# --------------------------------
# 3. LOADING AND PREPARING THE DATA
# --------------------------------
@st.cache_data
def load_data():
    # df = pd.read_csv('NorthAmericaViatorProducts.csv')
    df = pd.read_csv('NorthAmericaViatorProducts_with_country.csv')

    
    # We no longer split location into city/country.
    # Instead we just treat 'location' as 'city'.
    # If your "location" is more like "Whistler, British Columbia",
    # now "city" == "Whistler, British Columbia" for consistency.
    df["city"] = df["location"]
    
    
    # Standardize column names
    # (We do NOT rename 'rating_exact_score' → 'rating_score' here,
    #  because your CSV already has 'rating_score'.)
    df = df.rename(columns={
        'rating_review_count': 'total_reviews',
        'title': 'tour_name'
    })
    
    # Convert rating_score to numeric (coerce invalid to NaN, fill with 0)
    df["rating_score"] = pd.to_numeric(df["rating_score"], errors="coerce").fillna(0)
    
    # Fill NaN in 'category' with 'Uncategorized'
    df['category'] = df['category'].fillna('Uncategorized').astype(str)
    
    # Drop duplicates
    df = df.drop_duplicates(subset=['tour_name'], keep='first')
    
    return df

df = load_data()

# -----------------------
# 4. TITLE AND DESCRIPTION
# -----------------------
st.title("🗺️ Viator North America Visualization")
st.markdown("*Last Update: 16 Jan 2025*")
st.markdown("""
This dashboard analyzes Viator's tour offerings across North America.
""")

# ---------------------------
# 5. SIDEBAR FILTERS & SEARCH
# ---------------------------
with st.sidebar:
    # st.header("Analysis Filters")
    
    # Review Count Filter
    st.subheader("Review Count Filter")
    min_reviews = int(df["total_reviews"].min())
    max_reviews = int(df["total_reviews"].max())
    review_range = st.slider(
        "Total Review Count Range",
        min_reviews,
        max_reviews,
        (min_reviews, max_reviews)
    )
    
    # Rating Filter
    st.subheader("Rating Score Filter")
    min_rating = float(df["rating_score"].min())
    max_rating = float(df["rating_score"].max())
    selected_rating_range = st.slider(
        "Select rating score range",
        min_rating,
        max_rating,
        (min_rating, max_rating),
        step=0.1
    )
    
    # Country Filter
    st.subheader("Geographic Filters")
    countries = sorted(df["country"].dropna().unique())
    selected_countries = st.multiselect(
        "Select Countries",
        ["All"] + list(countries),
        default="All"
    )
    
    # Category Filter
    categories = sorted(df["category"].unique())
    selected_categories = st.multiselect(
        "Select Categories",
        ["All"] + list(categories),
        default="All"
    )
    
    # # Visualization Settings
    st.subheader("Visualization Settings")
    
    sort_options = {
        "Total Reviews": "total_reviews",
        "Rating Score": "rating_score",
        "Total Tours": "total_tours"
    }
    sort_column = st.selectbox("Sort Data by", list(sort_options.keys()))
    
    sort_order = st.selectbox("Sort Order", ["Descending", "Ascending"])
    
    # # Search Bar
    # st.subheader("Search by Keyword")
    # search_query = st.text_input("🔎 Search tours/cities (optional)")

# --------------------------
# 6. APPLY FILTERS TO DATAFRAME
# --------------------------
filtered_df = df.copy()

# Country
if "All" not in selected_countries:
    filtered_df = filtered_df[filtered_df["country"].isin(selected_countries)]

# Category
if "All" not in selected_categories:
    filtered_df = filtered_df[filtered_df["category"].isin(selected_categories)]

# Review range
filtered_df = filtered_df[
    (filtered_df["total_reviews"] >= review_range[0]) &
    (filtered_df["total_reviews"] <= review_range[1])
]

# Rating range
filtered_df = filtered_df[
    (filtered_df["rating_score"] >= selected_rating_range[0]) &
    (filtered_df["rating_score"] <= selected_rating_range[1])
]

# # Keyword Search
# if search_query:
#     query_lower = search_query.lower()
#     filtered_df = filtered_df[
#         filtered_df["tour_name"].str.lower().str.contains(query_lower) |
#         filtered_df["city"].str.lower().str.contains(query_lower)
#     ]

# ---------------------------
# 7. CALCULATE CITY METRICS
# ---------------------------
try:
    # Group by city and country to get tour counts
    tour_counts = filtered_df.groupby(["city", "country"]).size().reset_index(name="total_tours")
    
    # Aggregated metrics
    city_stats = filtered_df.groupby(["city", "country"]).agg({
        "total_reviews": "sum",
        "rating_score": "mean",
        "latitude": "first",
        "longitude": "first"
    }).reset_index()
    
    # Most common category per city
    city_categories = filtered_df.groupby(["city", "country"])["category"].apply(
        lambda x: x.mode().iloc[0] if not x.empty else "Uncategorized"
    ).reset_index()
    
    # Merge all metrics
    city_metrics = tour_counts.merge(city_stats, on=["city", "country"])
    city_metrics = city_metrics.merge(city_categories, on=["city", "country"])
    
    # Fill NaN if any
    city_metrics = city_metrics.fillna({
        "total_tours": 0,
        "total_reviews": 0,
        "rating_score": 0,
        "category": "Uncategorized"
    })
    
except Exception as e:
    st.error(f"Error calculating city metrics: {str(e)}")
    st.stop()

# ------------------------------------------------
# 8. TABS FOR MAP, RANKINGS, CATEGORY, HIERARCHY...
# ------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Map", 
    "Detailed Rankings", 
    "Category Analysis", 
    "Tour Hierarchy", 
    "Reviews vs Ratings"
])

# ---- Tab 1: Map ----
with tab1:
    st.header("Cities in North America with Viator Tours – Highlighted by Number of Tours")
    st.markdown("*Hover over circles to see city stats. Color bar on the right shows total tours.*")

    # Sort city_metrics for consistent sizing
    city_metrics_sorted = city_metrics.sort_values("total_tours", ascending=True)

    # Create a "circle_size" so bigger circles == more tours
    city_metrics_sorted["circle_size"] = (city_metrics_sorted["total_tours"] * 0.5).clip(lower=2)

    # Drop rows missing lat/lon to avoid Plotly errors
    city_metrics_sorted = city_metrics_sorted.dropna(subset=["latitude", "longitude"])

    # Build the figure
    fig_map = px.scatter_mapbox(
        city_metrics_sorted,
        lat="latitude",
        lon="longitude",
        size="circle_size",
        color="total_tours",            # color scale based on total_tours
        hover_name="city",              # city name appears on hover
        hover_data={
            "country": True,
            "total_tours": True,
            "total_reviews": True,
            "rating_score": ":.2f"
        },
        color_continuous_scale="Viridis",
        size_max=40,
        zoom=3.5,  
        center={"lat": 30, "lon": -95},  # Adjust for NA
        labels={"total_tours": "TotalCityTourCount"}
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        height=600,
        margin={"r":0, "t":0, "l":0, "b":0},
    )

    fig_map.update_layout(
        coloraxis_colorbar=dict(
            title="TotalCityTourCount",
            orientation="v",
            yanchor="middle",
            xanchor="left",
            x=0.98,
            y=0.5
        )
    )

    st.plotly_chart(fig_map, use_container_width=True)

# ---- Tab 2: Detailed Rankings ----
with tab2:
    st.header("📊 Detailed Rankings")
    
    # Sorting logic for 'Most Popular Tours'
    sort_options = {
        "Total Reviews": "total_reviews",
        "Rating Score": "rating_score",
        "Total Tours": "total_tours"
    }
    sort_col = sort_options[sort_column]
    ascending_bool = (sort_order == "Ascending")
    
    st.subheader("Most Popular Tours in North America")
    if sort_column == "Total Tours":
        city_ordered = city_metrics.sort_values(
            "total_tours", ascending=ascending_bool
        )[["city", "total_tours"]]
        sorted_tours = pd.merge(
            filtered_df, city_ordered, on="city"
        ).sort_values("total_tours", ascending=ascending_bool)
    else:
        sorted_tours = filtered_df.sort_values(sort_col, ascending=ascending_bool)
        sorted_tours = pd.merge(
            sorted_tours,
            city_metrics[["city", "total_tours"]],
            on="city",
            how="left"
        )
    
    tours_display = sorted_tours[[
        "country", "city", "category", 
        "rating_score", "total_reviews", "tour_name", "total_tours"
    ]].copy()
    
    tours_display.insert(0, "Position", range(1, len(tours_display) + 1))
    
    st.dataframe(tours_display, use_container_width=True, hide_index=True)
    
    st.subheader("Most Popular Cities in North America (Grouped by City)")
    # Group by city (and country), aggregating columns
    popular_cities_grouped = filtered_df.groupby(
        ["city", "country"], as_index=False
    ).agg({
        "tour_name": "count",
        "total_reviews": "sum",
        "rating_score": "mean",
        "category": lambda cats: ", ".join(sorted(set(cats)))
    })
    
    popular_cities_grouped = popular_cities_grouped.rename(columns={
        "tour_name": "total_tours"
    })
    
    popular_cities_grouped = popular_cities_grouped.sort_values(
        "total_reviews", ascending=False
    )
    
    popular_cities_grouped.insert(0, "Position", range(1, len(popular_cities_grouped) + 1))
    
    st.dataframe(
        popular_cities_grouped[[
            "Position", "city", "country",
            "total_reviews", "rating_score",
            "total_tours", "category"
        ]],
        use_container_width=True,
        hide_index=True
    )

# ---- Tab 3: Category Analysis ----
with tab3:
    st.header("📈 Category Analysis")
    
    # Keep the Treemap if you like it
    category_metrics = filtered_df.groupby("category").agg({
        "tour_name": "count",
        "rating_score": "mean",
        "total_reviews": "sum"
    }).reset_index().rename(columns={
        "tour_name": "total_tours"
    })
    
    fig_treemap = px.treemap(
        category_metrics,
        path=["category"],
        values="total_tours",
        color="rating_score",
        color_continuous_scale="RdYlBu",
        title="Distribution of Tours by Category"
    )
    st.plotly_chart(fig_treemap, use_container_width=True)
    
    # NEW: A bar chart showing top cities by total tours
    # st.subheader("Top Cities by Tour Count")
    
    # Sort city_metrics by total_tours descending and pick e.g. top 15
    # top_cities = city_metrics.sort_values("total_tours", ascending=False).head(15)
    
    # # Create a horizontal bar chart
    # fig_cities = px.bar(
    #     top_cities,
    #     y="city",
    #     x="total_tours",
    #     color="rating_score",  # color scale by avg. rating
    #     orientation="h",
    #     hover_data=["country", "total_reviews", "rating_score"],
    #     color_continuous_scale="Blues",
    #     title="Top 15 Cities by Total Tours"
    # )
    # fig_cities.update_layout(
    #     xaxis_title="Total Tours",
    #     yaxis_title="City",
    #     # Move color bar/legend
    #     coloraxis_colorbar=dict(title="Avg Rating Score"),
    #     margin={"r":0, "t":50, "l":0, "b":0},
    #     showlegend=False
    # )
    # st.plotly_chart(fig_cities, use_container_width=True)


# ---- Tab 4: Tour Hierarchy (Sunburst) ----
with tab4:
    st.header("🔍 Tour Hierarchy")
    st.markdown("*Interactive visualization showing the relationship between countries, cities, and tour categories*")
    
    sunburst_data = filtered_df.groupby(["country", "city", "category"]).size().reset_index(name="count")
    
    # Option A: Set width and height in the px.sunburst call
    fig_sunburst = px.sunburst(
        sunburst_data,
        path=["country", "city", "category"],
        values="count",
        title="Hierarchical View of Tours (Best to filter a single country)",
        width=900,   # Increase width
        height=700   # Increase height
    )
    
    # Option B: (Alternative) use update_layout
    # fig_sunburst.update_layout(
    #     width=900,
    #     height=700
    # )

    # If you do NOT want the chart to shrink to the container width, set use_container_width=False
    st.plotly_chart(fig_sunburst, use_container_width=False)


with tab5:
    st.header("⭐ Reviews vs Ratings")
    st.markdown("*Relationship between average rating and total reviews across categories*")

    # 1. Group by category
    cat_agg_all = filtered_df.groupby("category", as_index=False).agg({
        "rating_score": "mean",
        "total_reviews": "sum"
    }).rename(columns={
        "rating_score": "avg_rating",
        "total_reviews": "sum_reviews"
    })

    # 2. Separate out "Self-guided Tours" from others
    sgt_df = cat_agg_all[cat_agg_all["category"] == "Self-guided Tours"]
    others_df = cat_agg_all[cat_agg_all["category"] != "Self-guided Tours"]

    # 3. Sort the 'others' by sum_reviews and take top N
    top_n = 20
    others_top = others_df.sort_values("sum_reviews", ascending=False).head(top_n)

    # 4. Combine the top categories plus "Self-guided Tours"
    #    If "Self-guided Tours" is already in top 20, it won't get duplicated.
    cat_agg_final = pd.concat([others_top, sgt_df]).drop_duplicates()

    # 5. Build the scatter plot
    fig_scatter = px.scatter(
        cat_agg_final,
        x="sum_reviews",
        y="avg_rating",
        color="category",
        size="sum_reviews",
        hover_data=["category", "sum_reviews", "avg_rating"],
        text="category",
        title=f"Reviews vs Ratings by Category (Top {top_n} + Self-guided Tours)"
    )

    # 6. Layout tweaks
    fig_scatter.update_layout(
        width=1100,
        height=700,
        xaxis_title="Total Reviews (Summed per Category)",
        yaxis_title="Average Rating Score",
        legend_title_text="Category",
    )

    # 7. Label styling
    fig_scatter.update_traces(
        textposition="top center",
        textfont=dict(
            family="Arial",
            size=12,
            color="white"
        )
    )

    st.plotly_chart(fig_scatter, use_container_width=False)






# ----------------
# 9. FOOTER
# ----------------
st.markdown("---")
st.markdown("*Data sourced from Viator's North American tour offerings.*")
