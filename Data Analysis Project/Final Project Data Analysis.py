import pandas as pd
from sqlalchemy import create_engine

# 1. Setup Connection (Change server and database if needed)
engine = create_engine(
    "mssql+pyodbc://@./AdventureWorksDW2022?driver=ODBC+Driver+17+for+SQL+Server"
)

# 2. Read data from SQL View into Pandas DataFrame
df = pd.read_sql_table("FactInternetSales", con=engine)
print("Data successfully read from SQL!")


#==================================================================================================


print("\n--- Data Quality Checks ---\n")

# 1. Inspect for missing values
print("Missing values per column:")
print(df.isnull().sum())

# 2. Check for duplicate rows
num_duplicates = df.duplicated().sum()
print(f"\nTotal duplicate rows: {num_duplicates}")

# 3. Examine column data types (re-displaying info for context of this step)
print("\nColumn information and data types:")
df.info()

# 4. Look for negative or invalid numeric values in relevant columns
# Identify numerical columns that should typically not be negative
numeric_cols_to_check = [
    'SalesAmount', 'OrderQuantity', 'UnitPrice', 'ProductStandardCost', 'DiscountAmount'
]

print("\nChecking for negative values in key numeric columns:")
for col in numeric_cols_to_check:
    if df[col].dtype in ['int64', 'float64']:
        negative_values_count = (df[col] < 0).sum()
        if negative_values_count > 0:
            print(f"  Column '{col}': {negative_values_count} negative values found.")
    else:
        print(f"  Column '{col}' is not a numeric type, skipping negative value check.")

# 5. Perform basic consistency checks / summary statistics
print("\nBasic descriptive statistics for numeric columns:")
print(df.describe())


#==================================================================================================


print("\n--- Step 4: Data Preprocessing ---\n")

# 1. Rename selected columns to be more descriptive and user-friendly
df.rename(columns={
    'OrderQuantity': 'Order Quantity',
    'UnitPrice': 'Unit Price',
    'SalesAmount': 'Sales Amount',
    'TaxAmt': 'Tax Amount',
    'Freight': 'Freight Amount',
    'DiscountAmount': 'Discount Amount',
    'ProductStandardCost': 'Product Standard Cost'
}, inplace=True)
print("Columns renamed for clarity.")

# 3. Handle missing values
# For simplicity, fill numeric NaNs with 0. More sophisticated imputation methods
# (e.g., mean, median, mode, or predictive imputation) could be used based on analysis.
print("\nHandling missing values:")
initial_missing_counts = df.isnull().sum()

for col in df.select_dtypes(include=['number']).columns:
    if df[col].isnull().any():
        df[col].fillna(0, inplace=True)
        print(f"  Filled missing numeric values in '{col}' with 0.")

# If any critical identifier columns have NaNs, one might drop those rows

# Display updated missing value counts (should be mostly 0 for numerics now)
print("Updated missing values per column after initial handling:")
print(df.isnull().sum()) 

# 4. Remove duplicate records
initial_rows = len(df)
df.drop_duplicates(inplace=True)
num_duplicates_removed = initial_rows - len(df)
print(f"\nRemoved {num_duplicates_removed} duplicate rows.")

# 5. Select only the columns that will be relevant and necessary for the final reporting table
# This list includes original columns and those needed for feature engineering in Step 5.
selected_columns = [
    'ProductKey',
    'OrderDateKey',
    'DueDateKey',
    'ShipDateKey',
    'CustomerKey',
    'SalesTerritoryKey',
    'SalesOrderNumber',
    'SalesOrderLineNumber',
    'Order Quantity',
    'Unit Price',
    'TotalProductCost',
    'Sales Amount',
    'Discount Amount',
    'Tax Amount',
    'Freight Amount',
    'OrderDate',
    'DueDate',
    'ShipDate',
    'Product Standard Cost'
]

# Ensure all selected columns exist before filtering
selected_columns = [col for col in selected_columns if col in df.columns]
df = df[selected_columns]


#==================================================================================================


# 1. Calculate Profit for each transaction
# Profit = Sales Amount - TotalProductCost - Discount Amount 
df['Profit'] = df['Sales Amount'] - df['TotalProductCost'] - df['Discount Amount']

# 2. Calculate Discount Percentage
# Handle division by zero for 'Sales Amount'
df['Discount Percentage'] = (df['Discount Amount'] / df['Sales Amount']).fillna(0)
df['Discount Percentage'].replace([float('inf'), -float('inf')], 0, inplace=True) # Handle actual division by zero results
df['Discount Percentage'] = (df['Discount Percentage'] * 100).round(2) # as a percentage, rounded to 2 decimals

# 3. Derive Order Year, Order Month, and Order Quarter from 'Order Date'
df['Order Year'] = df['OrderDate'].dt.year
df['Order Month'] = df['OrderDate'].dt.month
df['Order Quarter'] = df['OrderDate'].dt.quarter

# 4. Create Sales Category based on Sales Amount
# Example: >1000 = 'High', >200 = 'Medium', <=200 = 'Low'
sales_bins = [0, 200.01, 1000.01, float('inf')] # Adjusted bins to ensure all values fall into a category
sales_labels = ['Low', 'Medium', 'High']
df['Sales Category'] = pd.cut(df['Sales Amount'], bins=sales_bins, labels=sales_labels, right=False, include_lowest=True)

# 5. Add two other simple reporting features
# Feature 7a: Days to Ship
df['DaysToShip'] = (df['ShipDate'] - df['OrderDate']).dt.days.fillna(0).astype(int)

df['LineItemTotal'] = df['Order Quantity'] * df['Unit Price']


#==================================================================================================


# 3. Write data back to a new SQL Table
df.to_sql(
    name="PythonSalesReportingTable",
    con=engine,
    if_exists="replace",
    index=False,
)
print("Data successfully written to SQL table!")
