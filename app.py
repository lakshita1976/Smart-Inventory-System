import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import date
from sklearn.linear_model import LinearRegression
import boto3
import os
S3_BUCKET = "smart-inventory-lakshita-2026-xyz"
AWS_REGION = "us-east-1"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION
)
def upload_to_s3(file_path):
    file_name = os.path.basename(file_path)
    s3.upload_file(file_path, S3_BUCKET, file_name)
st.set_page_config(
    page_title="Smart Inventory System",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Smart Inventory Expiry, Defect Analysis and Demand Prediction System")
st.write("Monitor inventory, analyse product defects, and predict future demand.")

@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"])
    return df

st.sidebar.header("Inventory Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload Inventory CSV",
    type=["csv"]
)

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.sidebar.success("Custom inventory loaded successfully!")
else:
    df = load_data("inventory.csv")
    st.sidebar.info("Using the default inventory dataset.")

# Inventory calculations
df["Usable_Stock"] = df["Stock"] - df["Defective_Units"]
df["Defect_Percentage"] = (
    df["Defective_Units"] / df["Stock"].replace(0, np.nan)
) * 100

df["Days_To_Expiry"] = (
    df["Expiry_Date"] - pd.Timestamp(date.today())
).dt.days

df["Expiry_Status"] = df["Days_To_Expiry"].apply(
    lambda days: "Expired" if days < 0
    else "Near Expiry" if days <= 7
    else "Valid"
)

df["Stock_Status"] = df.apply(
    lambda row: "Out of Stock" if row["Usable_Stock"] <= 0
    else "Low Stock" if row["Usable_Stock"] < row["Daily_Sales"] * 3
    else "Normal",
    axis=1
)

# Sidebar
st.sidebar.header("Navigation")

page = st.sidebar.radio(
    "Select Section",
    [
        "Dashboard",
        "Expiry Monitoring",
        "Defect Analysis",
        "Demand Prediction",
        "Inventory Records",
        "Add Product",
        "Delete Product"
    ]
)

# Dashboard
if page == "Dashboard":

    st.subheader("Inventory Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Products", len(df))
    col2.metric("Total Stock", int(df["Stock"].sum()))
    col3.metric("Defective Units", int(df["Defective_Units"].sum()))
    col4.metric("Near-Expiry Products", int((df["Expiry_Status"] == "Near Expiry").sum()))

    st.subheader("Stock by Product")

    fig = px.bar(
        df,
        x="Product_Name",
        y="Usable_Stock",
        color="Category",
        title="Usable Stock by Product"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Inventory Alerts")

    alerts = df[
        (df["Expiry_Status"] != "Valid")
        | (df["Stock_Status"] != "Normal")
        | (df["Defect_Percentage"] >= 10)
    ]
    def get_priority(row):
        if row["Expiry_Status"] == "Expired":
            return "Critical"
        elif row["Days_To_Expiry"] <= 1:
            return "Critical"
        elif (
            row["Stock_Status"] in ["Low Stock", "Out of Stock"]
            or row["Defect_Percentage"] >= 10
            or row["Expiry_Status"] == "Near Expiry"
        ):
            return "High"
        else:
            return "Normal"

    alerts = alerts.copy()

    if not alerts.empty:
        alerts["Priority"] = alerts.apply(get_priority, axis=1)

        priority_order = {"Critical": 0, "High": 1, "Normal": 2}
        alerts["Priority_Order"] = alerts["Priority"].map(priority_order)
        alerts = alerts.sort_values("Priority_Order")

    if alerts.empty:
        st.success("No inventory alerts.")
    else:
        st.dataframe(
            alerts[
                [
                    "Product_Name",
                    "Usable_Stock",
                    "Defective_Units",
                    "Defect_Percentage",
                    "Expiry_Status",
                    "Stock_Status",
                    "Priority"
                ]
            ],
            use_container_width=True
        )

# Expiry Monitoring
elif page == "Expiry Monitoring":

    st.subheader("Product Expiry Monitoring")

    expiry_filter = st.selectbox(
        "Select Expiry Status",
        ["All", "Expired", "Near Expiry", "Valid"]
    )

    result = df.copy()

    if expiry_filter != "All":
        result = result[result["Expiry_Status"] == expiry_filter]

    st.dataframe(
        result[
            [
                "Product_Name",
                "Stock",
                "Expiry_Date",
                "Days_To_Expiry",
                "Expiry_Status"
            ]
        ],
        use_container_width=True
    )

    st.subheader("Expiry Status Distribution")

    fig = px.pie(
        df,
        names="Expiry_Status",
        title="Product Expiry Distribution"
    )

    st.plotly_chart(fig, use_container_width=True)

# Defect Analysis
elif page == "Defect Analysis":

    st.subheader("Product Defect Analysis")

    total_stock = df["Stock"].sum()
    total_defects = df["Defective_Units"].sum()

    defect_rate = (
        total_defects / total_stock * 100
        if total_stock > 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Products in Stock", int(total_stock))
    col2.metric("Defective Units", int(total_defects))
    col3.metric("Overall Defect Rate", f"{defect_rate:.2f}%")

    fig = px.bar(
        df,
        x="Product_Name",
        y="Defect_Percentage",
        color="Category",
        title="Defect Percentage by Product"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Products Requiring Quality Inspection")

    defective_products = df[df["Defective_Units"] > 0]

    st.dataframe(
        defective_products[
            [
                "Product_Name",
                "Stock",
                "Defective_Units",
                "Defect_Percentage"
            ]
        ],
        use_container_width=True
    )

# Demand Prediction
elif page == "Demand Prediction":

    st.subheader("Historical Sales-Based Demand Prediction")

    try:
        sales_df = pd.read_csv("sales_history.csv")

        product = st.selectbox(
            "Select Product",
            df["Product_Name"].tolist()
        )

        selected = df[df["Product_Name"] == product].iloc[0]

        product_sales = sales_df[
            sales_df["Product_ID"] == selected["Product_ID"]
        ].copy()

        if len(product_sales) < 5:
            st.warning(
                "Insufficient historical sales data for this product."
            )

        else:
            X = product_sales[["Day"]]
            y = product_sales["Units_Sold"]

            model = LinearRegression()
            model.fit(X, y)

            future_days = pd.DataFrame({
                "Day": range(
                    int(product_sales["Day"].max()) + 1,
                    int(product_sales["Day"].max()) + 8
                )
            })

            predictions = np.maximum(
                0,
                model.predict(future_days)
            )

            prediction_df = pd.DataFrame({
                "Day": future_days["Day"],
                "Predicted_Demand": np.round(predictions, 2)
            })

            col1, col2 = st.columns(2)

            col1.metric(
                "Average Historical Sales",
                f"{y.mean():.2f} units/day"
            )

            col2.metric(
                "Average Predicted Demand",
                f"{predictions.mean():.2f} units/day"
            )

            historical_fig = px.line(
                product_sales,
                x="Day",
                y="Units_Sold",
                markers=True,
                title="Historical Sales"
            )

            st.plotly_chart(
                historical_fig,
                use_container_width=True
            )

            st.subheader("Next Seven Days Prediction")

            st.dataframe(
                prediction_df,
                use_container_width=True
            )

            required_stock = predictions.sum()

            usable_stock = max(
                0,
                selected["Stock"] - selected["Defective_Units"]
            )

            additional_stock = max(
                0,
                np.ceil(required_stock - usable_stock)
            )

            st.subheader("Intelligent Inventory Recommendation")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Current Usable Stock",
                f"{usable_stock:.0f} units"
            )

            col2.metric(
                "Predicted 7-Day Demand",
                f"{required_stock:.0f} units"
            )

            col3.metric(
                "Additional Stock Required",
                f"{additional_stock:.0f} units"
            )

            if additional_stock > 0:
                st.warning(
                    f"⚠️ Recommendation: Purchase "
                    f"{additional_stock:.0f} additional units of {product}."
                )
            else:
                st.success(
                    f"✅ Current usable stock of {product} "
                    "is sufficient for the predicted demand."
                )

    except FileNotFoundError:
        st.error(
            "sales_history.csv was not found. "
            "Create the file in your project folder."
        )
# Inventory Records
elif page == "Inventory Records":

    st.subheader("Complete Inventory Records")

    st.dataframe(
        df,
        use_container_width=True
    )

    st.download_button(
        "Download Inventory Report",
        data=df.to_csv(index=False),
        file_name="inventory_report.csv",
        mime="text/csv"
    )
elif page == "Add Product":

    st.subheader("Add New Inventory Product")

    with st.form("add_product_form", clear_on_submit=True):

        product_id = st.text_input("Product ID").strip()
        product_name = st.text_input("Product Name").strip()

        category = st.selectbox(
            "Category",
            ["Dairy", "Snacks", "Beverages", "Bakery", "Other"]
        )

        stock = st.number_input(
            "Stock Quantity",
            min_value=0,
            step=1
        )

        defective_units = st.number_input(
            "Defective Units",
            min_value=0,
            step=1
        )

        daily_sales = st.number_input(
            "Average Daily Sales",
            min_value=0,
            step=1
        )

        expiry_date = st.date_input("Expiry Date")

        submitted = st.form_submit_button("Add Product")

    if submitted:

        if not product_id or not product_name:
            st.error("Please enter the product ID and name.")

        elif stock < defective_units:
            st.error("Defective units cannot exceed total stock.")

        elif product_id in df["Product_ID"].astype(str).str.strip().values:
            st.error("This Product ID already exists.")

        else:

            new_product = pd.DataFrame([{
                "Product_ID": product_id,
                "Product_Name": product_name,
                "Category": category,
                "Stock": stock,
                "Defective_Units": defective_units,
                "Daily_Sales": daily_sales,
                "Expiry_Date": pd.Timestamp(expiry_date)
            }])

            updated_df = pd.concat(
                [df, new_product],
                ignore_index=True
            )

            updated_df.to_csv("inventory.csv", index=False)
            upload_to_s3("inventory.csv")

            st.cache_data.clear()

            st.success(f"Product '{product_name}' added successfully!")

            st.rerun()
elif page == "Delete Product":

    st.subheader("Delete Inventory Product")

    product_ids = df["Product_ID"].astype(str).tolist()

    if not product_ids:
        st.info("No products available to delete.")

    else:
        selected_id = st.selectbox(
            "Select Product ID",
            product_ids
        )

        selected_product = df[
            df["Product_ID"].astype(str) == selected_id
        ].iloc[0]

        st.write("Product Name:", selected_product["Product_Name"])
        st.write("Current Stock:", selected_product["Stock"])

        confirm = st.checkbox(
            "I confirm that I want to delete this product."
        )

        if st.button("Delete Product"):

            if confirm:

                updated_df = df[
                    df["Product_ID"].astype(str) != selected_id
                ]

                updated_df.to_csv("inventory.csv", index=False)
                upload_to_s3("inventory.csv")

                st.cache_data.clear()

                st.success(
                    f"Product {selected_id} deleted successfully."
                )

                st.rerun()

            else:
                st.warning("Please confirm before deleting.")


# AWS S3 Cloud Sync
st.sidebar.divider()
st.sidebar.subheader("AWS Cloud Sync")

if st.sidebar.button("Sync CSV Files to S3"):
    try:
        upload_to_s3("inventory.csv")
        upload_to_s3("sales_history.csv")
        st.sidebar.success("Files uploaded to AWS S3!")
    except Exception as e:
        st.sidebar.error(f"Upload failed: {e}")