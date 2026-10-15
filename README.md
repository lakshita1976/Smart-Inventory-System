# Smart Inventory Expiry, Defect Analysis and Demand Prediction System

## Project Overview
A Python-based inventory management system that monitors
product expiry, analyses defects, and predicts future demand.

## Features
- Inventory dashboard
- Product expiry monitoring
- Defect percentage analysis
- Seven-day demand prediction
- Intelligent inventory recommendations
- Add and delete products
- Inventory report download
- AWS S3 cloud synchronization

## Technologies Used
- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- Scikit-learn
- Linear Regression
- AWS S3
- Boto3

## Installation
Install the required libraries:

pip install -r requirements.txt

## Run the Application
Run this command in the project folder:

streamlit run app.py

## AWS Configuration
Configure valid AWS credentials to use the S3 synchronization
feature. AWS Academy temporary credentials may expire.

## Data Files
- inventory.csv
- sales_history.csv