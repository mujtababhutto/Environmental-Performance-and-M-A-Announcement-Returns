# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 23:46:48 2025

@author: vonpr
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np

# Import data
ma = pd.read_csv("MA Deals 11022025.csv", delimiter=",")

sp = pd.read_excel("Index.xlsx")
sp["Date"] = pd.to_datetime(sp["Date"], format="%d/%m/%Y", errors="coerce")
sp.set_index("Date", inplace=True)

stock = pd.read_excel("Stock Data US.xlsx")
stock["Date"] = pd.to_datetime(stock["Date"], format="%d/%m/%Y", errors="coerce")
stock.set_index("Date", inplace=True)

industry = pd.read_excel("Industry.xlsx")
industry.rename(columns={industry.columns[0]: "Acquirer Ticker"}, inplace=True)
industry["Acquirer Ticker"] = industry["Acquirer Ticker"].str.replace(r"\s*Equity\s*", "", regex=True)
industry.drop(columns=industry.columns[1:3], inplace=True)
industry.rename(columns={
    "industry_sector().value": "Acquirer Industry Sector",
    "industry_group().value": "Acquirer Industry Group",
    "industry_subgroup().value": "Acquirer Industry Subgroup"
}, inplace=True)

esg = pd.read_excel("ESG.xlsx")

# Merging

# Standardize tickers before merging
ma["Acquirer Ticker"] = ma["Acquirer Ticker"].astype(str).str.upper().str.strip()
ma["Target Ticker"] = ma["Target Ticker"].astype(str).str.upper().str.strip()
esg.index = esg.index.astype(str).str.upper().str.strip()

# Reset index so ESG dataset can be merged properly
esg_reset = esg.reset_index()

# Merge ESG data for Acquirer
df_merged = ma.merge(esg_reset, left_on="Acquirer Ticker", right_on="Ticker", how="left")
df_merged.rename(columns={
    "SP_R_ESG_RANK": "Acquirer_ESG_Rank",
    "TOT_GHG_CO2_EM_INTENS_PER_SALES": "Acquirer_CO2_Sales"
}, inplace=True)
df_merged.drop(columns=["Ticker"], inplace=True)  # Remove duplicate column
df_merged = df_merged.merge(industry, on="Acquirer Ticker", how="left")

# Drop rows where both "Acquirer_ESG_Rank" and "Acquirer_CO2_Sales" are NaN
df_filtered = df_merged.dropna(subset=["Acquirer_ESG_Rank", "Acquirer_CO2_Sales"], how="all")

# Event Window

# Ensure stock and S&P 500 index are properly formatted
stock.index = pd.to_datetime(stock.index, errors="coerce")
sp.index = pd.to_datetime(sp.index, errors="coerce")

# Merge S&P 500 into stock data based on the Date index
stock = stock.merge(sp, left_index=True, right_index=True, how="left")
stock["Last Price"] = stock["Last Price"].replace(",", "", regex=True).astype(float)


# Verify that the correct benchmark is used
benchmark_ticker = "Last Price"  # Adjust if needed
if benchmark_ticker not in stock.columns:
    raise ValueError(f"Benchmark ticker '{benchmark_ticker}' not found after merging S&P 500.")

print(f"Using '{benchmark_ticker}' as the benchmark.")

# Ensure "Announce Date" is in datetime format
df_filtered = df_filtered.copy()  # Avoid SettingWithCopyWarning
df_filtered.loc[:, "Announce Date"] = pd.to_datetime(df_filtered["Announce Date"], errors="coerce")

# Define event window (-20 to +20 days around announcement)
event_window = list(range(-20, 21))

# Initialize new columns for CAR calculations
df_filtered = df_filtered.assign(**{"CAR [-2,+2]": None, "CAR [-10,+10]": None})

# Dictionary to store abnormal returns
abnormal_returns_dict = {}

# Iterate over each M&A deal in df_filtered
for idx, row in df_filtered.iterrows():
    acquirer_ticker = row["Acquirer Ticker"]
    announce_date = row["Announce Date"]

    if acquirer_ticker in stock.columns:
        # Define event window date range
        date_range = [announce_date + pd.Timedelta(days=i) for i in event_window]

        # Extract and clean stock prices
        stock_prices = stock[acquirer_ticker].reindex(date_range).dropna()
        if len(stock_prices) < 2:
            continue  # Skip if insufficient stock data

        # Calculate stock returns
        stock_returns = stock_prices.pct_change().dropna()

        # Extract and clean benchmark prices from sp
        sp_prices_clean = stock[benchmark_ticker].reindex(date_range).dropna()
        if len(sp_prices_clean) < 2:
            continue  # Skip if insufficient market data

        # Calculate market returns
        market_returns = sp_prices_clean.pct_change().dropna()

        # Align stock and market returns to avoid NaN mismatches
        aligned_index = stock_returns.index.intersection(market_returns.index)
        stock_returns = stock_returns.loc[aligned_index]
        market_returns = market_returns.loc[aligned_index]

        # Compute abnormal returns (AR = Stock Return - Market Return)
        abnormal_returns = stock_returns - market_returns

        # Store abnormal returns
        abnormal_returns_dict[acquirer_ticker] = abnormal_returns

        # Compute CAR for [-2,+2] and [-10,+10] windows
        car_2 = abnormal_returns.loc[announce_date - pd.Timedelta(days=2) : announce_date + pd.Timedelta(days=2)].sum()
        car_10 = abnormal_returns.loc[announce_date - pd.Timedelta(days=10) : announce_date + pd.Timedelta(days=10)].sum()

        # Assign CAR values to df_filtered using .loc[]
        df_filtered.loc[idx, "CAR [-2,+2]"] = car_2
        df_filtered.loc[idx, "CAR [-10,+10]"] = car_10

# Drop rows where both CAR windows are NaN
df_filtered = df_filtered.dropna(subset=["CAR [-2,+2]", "CAR [-10,+10]"], how="all")
# Ensure numeric values for regression variables
df_filtered["CAR [-2,+2]"] = pd.to_numeric(df_filtered["CAR [-2,+2]"], errors="coerce")
df_filtered["CAR [-10,+10]"] = pd.to_numeric(df_filtered["CAR [-10,+10]"], errors="coerce")

# Compute industry-specific median thresholds for ESG Rank and CO₂ Sales
industry_medians = df_filtered.groupby("Acquirer Industry Sector")[["Acquirer_ESG_Rank", "Acquirer_CO2_Sales"]].median()

# Map industry-specific thresholds to each firm
df_filtered["Industry_ESG_Threshold"] = df_filtered["Acquirer Industry Sector"].map(industry_medians["Acquirer_ESG_Rank"])
df_filtered["Industry_CO2_Threshold"] = df_filtered["Acquirer Industry Sector"].map(industry_medians["Acquirer_CO2_Sales"])

# Industry-adjusted classification: Compare ESG & CO₂ against industry-specific medians
df_filtered["Green_Acquirer"] = df_filtered.apply(
    lambda row: 1 if (
        (pd.notna(row["Acquirer_ESG_Rank"]) and pd.notna(row["Acquirer_CO2_Sales"]) and 
         (row["Acquirer_ESG_Rank"] >= row["Industry_ESG_Threshold"]) and 
         (row["Acquirer_CO2_Sales"] <= row["Industry_CO2_Threshold"]))
        or (pd.isna(row["Acquirer_CO2_Sales"]) and row["Acquirer_ESG_Rank"] >= row["Industry_ESG_Threshold"])
        or (pd.isna(row["Acquirer_ESG_Rank"]) and row["Acquirer_CO2_Sales"] <= row["Industry_CO2_Threshold"])
    ) else 0, axis=1
)

# Drop the industry thresholds after classification to keep dataset clean
df_filtered.drop(columns=["Industry_ESG_Threshold", "Industry_CO2_Threshold"], inplace=True)

#Analyse


# Summary Statistics
summary_stats = df_filtered.describe()
print(summary_stats)

# Count Green vs. Non-Green Acquirers
green_counts = df_filtered["Green_Acquirer"].value_counts()

# Plot Distribution of ESG Rank and CO2 Sales
plt.figure(figsize=(12, 5))
sns.histplot(df_filtered["Acquirer_ESG_Rank"], bins=20, kde=True, color="green", label="ESG Rank")
sns.histplot(df_filtered["Acquirer_CO2_Sales"], bins=20, kde=True, color="red", label="CO2 Sales")
plt.legend()
plt.title("Distribution of ESG Rank and CO2 Sales")
plt.show()

# Plot Distribution of Deal Value
deal_value_column = "Announced Total Value (mil.)"
plt.figure(figsize=(10, 5))
sns.histplot(df_filtered[deal_value_column], bins=20, kde=True, color="blue")
plt.title("Distribution of M&A Deal Values")
plt.xlabel("Deal Value (in million USD)")
plt.show()

# Scatter plot: ESG Rank vs. CO2 Sales
plt.figure(figsize=(8, 6))
sns.scatterplot(x=df_filtered["Acquirer_ESG_Rank"], y=df_filtered["Acquirer_CO2_Sales"], hue=df_filtered["Green_Acquirer"])
plt.title("ESG Rank vs. CO2 Sales")
plt.xlabel("ESG Rank")
plt.ylabel("CO2 Sales")
plt.show()

# Correlation Heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(df_filtered.corr(numeric_only=True), annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Correlation Matrix")
plt.show()

# Regression Analysis


# Ensure numeric values for regression
df_filtered["CAR [-2,+2]"] = pd.to_numeric(df_filtered["CAR [-2,+2]"], errors="coerce")
df_filtered["CAR [-10,+10]"] = pd.to_numeric(df_filtered["CAR [-10,+10]"], errors="coerce")
df_filtered["Acquirer_ESG_Rank"] = pd.to_numeric(df_filtered["Acquirer_ESG_Rank"], errors="coerce")
df_filtered["Acquirer_CO2_Sales"] = pd.to_numeric(df_filtered["Acquirer_CO2_Sales"], errors="coerce")

# Drop missing values in regression variables
df_filtered = df_filtered.dropna(subset=["CAR [-2,+2]", "CAR [-10,+10]", "Acquirer_ESG_Rank", "Acquirer_CO2_Sales"])

# Convert Announce Date to Year and ensure it's an integer
df_filtered["Year"] = pd.to_datetime(df_filtered["Announce Date"], errors="coerce").dt.year
df_filtered = df_filtered.dropna(subset=["Year"])
df_filtered["Year"] = df_filtered["Year"].astype(int)

# Define deal value column and ensure it's numeric
deal_value_column = "Announced Total Value (mil.)"
df_filtered[deal_value_column] = pd.to_numeric(df_filtered[deal_value_column], errors="coerce")
df_filtered = df_filtered.dropna(subset=[deal_value_column])

# Log transformation for Deal Value
df_filtered["log_Deal_Value"] = df_filtered[deal_value_column].apply(lambda x: np.log(x) if x > 0 else np.nan)
df_filtered = df_filtered.dropna(subset=["log_Deal_Value"])

# **Set 2019 as the baseline year for Time Fixed Effects**
df_filtered["Year"] = df_filtered["Year"].astype("category")
df_filtered["Year"] = df_filtered["Year"].cat.set_categories(sorted(df_filtered["Year"].unique()))
df_filtered["Year"] = df_filtered["Year"].astype(int)  

# **Run Regressions without Green_Acquirer**
reg1 = smf.ols(f"Q('CAR [-2,+2]') ~ Acquirer_ESG_Rank + Acquirer_CO2_Sales + log_Deal_Value", data=df_filtered).fit()
reg2 = smf.ols(f"Q('CAR [-10,+10]') ~ Acquirer_ESG_Rank + Acquirer_CO2_Sales + log_Deal_Value", data=df_filtered).fit()

# **Regression with Time Fixed Effects (Using 2019 as Baseline)**
reg3 = smf.ols(f"Q('CAR [-2,+2]') ~ Acquirer_ESG_Rank + Acquirer_CO2_Sales + log_Deal_Value + C(Year, Treatment(2019))", data=df_filtered).fit()
reg4 = smf.ols(f"Q('CAR [-10,+10]') ~ Acquirer_ESG_Rank + Acquirer_CO2_Sales + log_Deal_Value + C(Year, Treatment(2019))", data=df_filtered).fit()

# Ensure Acquirer Industry Sector is categorical
df_filtered["Acquirer Industry Sector"] = df_filtered["Acquirer Industry Sector"].astype("category")

# Run Regression with Industry-Specific ESG Impact
reg_industry = smf.ols(
    "Q('CAR [-2,+2]') ~ Acquirer_ESG_Rank * C(Q('Acquirer Industry Sector')) + "
    "Acquirer_CO2_Sales * C(Q('Acquirer Industry Sector')) + log_Deal_Value",
    data=df_filtered
).fit()

# Print results
print(reg1.summary())
print(reg2.summary())
print(reg3.summary())
print(reg4.summary())
print(reg_industry.summary())

# Export regression results to Excel
reg_results = pd.DataFrame({
    "Model": ["CAR [-2,+2]", "CAR [-10,+10]", "CAR [-2,+2] (FE)", "CAR [-10,+10] (FE)"],
    "R-squared": [reg1.rsquared, reg2.rsquared, reg3.rsquared, reg4.rsquared],
    "ESG_Coeff": [reg1.params["Acquirer_ESG_Rank"], reg2.params["Acquirer_ESG_Rank"], reg3.params["Acquirer_ESG_Rank"], reg4.params["Acquirer_ESG_Rank"]],
    "CO2_Coeff": [reg1.params["Acquirer_CO2_Sales"], reg2.params["Acquirer_CO2_Sales"], reg3.params["Acquirer_CO2_Sales"], reg4.params["Acquirer_CO2_Sales"]],
    "P-Value ESG": [reg1.pvalues["Acquirer_ESG_Rank"], reg2.pvalues["Acquirer_ESG_Rank"], reg3.pvalues["Acquirer_ESG_Rank"], reg4.pvalues["Acquirer_ESG_Rank"]],
    "P-Value CO2": [reg1.pvalues["Acquirer_CO2_Sales"], reg2.pvalues["Acquirer_CO2_Sales"], reg3.pvalues["Acquirer_CO2_Sales"], reg4.pvalues["Acquirer_CO2_Sales"]],
})

print(reg_results)

# === DIFFERENCE-IN-DIFFERENCES (DiD) ANALYSIS ===

# Define Treatment & Post-Policy Period using Exact SEC ESG Regulation Date
sec_esg_cutoff = pd.to_datetime("2022-03-21")  # SEC ESG regulation announcement date
df_filtered["Post_SEC_ESG"] = (df_filtered["Announce Date"] >= sec_esg_cutoff).astype(int)  # 1 if after cutoff

# Define Treatment Group: Green Acquirers
df_filtered["DiD_Treat_Green"] = df_filtered["Green_Acquirer"]  # 1 if Green Acquirer, 0 otherwise

# Run Difference-in-Differences Model
reg_did1 = smf.ols(
    "Q('CAR [-2,+2]') ~ DiD_Treat_Green * Post_SEC_ESG + log_Deal_Value + C(Year, Treatment(2019))", 
    data=df_filtered
).fit()

# Print Summary
print("DiD Analysis: Green vs. Non-Green Acquirers (SEC ESG Rules - March 21, 2022)")
print(reg_did1.summary())

# Export DiD Results
did_results = pd.DataFrame({
    "R-squared": [reg_did1.rsquared],
    "DiD_Treat_Coeff": [reg_did1.params["DiD_Treat_Green"]],
    "Post_SEC_ESG_Coeff": [reg_did1.params["Post_SEC_ESG"]],
    "DiD_Interaction_Coeff": [reg_did1.params["DiD_Treat_Green:Post_SEC_ESG"]],
    "P-Value DiD": [reg_did1.pvalues["DiD_Treat_Green:Post_SEC_ESG"]]
})

print("DiD Regression Results:")
print(did_results)


#Histogramms


# Set the figure size
plt.figure(figsize=(12, 5))

# Histogram for CAR [-2,+2]
plt.subplot(1, 2, 1)
sns.histplot(df_filtered["CAR [-2,+2]"], bins=30, kde=True, color="blue")
plt.title("Distribution of CAR [-2,+2]")
plt.xlabel("CAR [-2,+2]")
plt.ylabel("Frequency")

# Histogram for CAR [-10,+10]
plt.subplot(1, 2, 2)
sns.histplot(df_filtered["CAR [-10,+10]"], bins=30, kde=True, color="green")
plt.title("Distribution of CAR [-10,+10]")
plt.xlabel("CAR [-10,+10]")
plt.ylabel("Frequency")

# Adjust layout and show plot
plt.tight_layout()
plt.show()

# Filter data for Green Acquirers
df_green = df_filtered[df_filtered["Green_Acquirer"] == 1]

# Set the figure size
plt.figure(figsize=(12, 5))

# Histogram for CAR [-2,+2] (Green Acquirers)
plt.subplot(1, 2, 1)
sns.histplot(df_green["CAR [-2,+2]"], bins=30, kde=True, color="blue")
plt.title("Distribution of CAR [-2,+2] (Green Acquirers)")
plt.xlabel("CAR [-2,+2]")
plt.ylabel("Frequency")

# Histogram for CAR [-10,+10] (Green Acquirers)
plt.subplot(1, 2, 2)
sns.histplot(df_green["CAR [-10,+10]"], bins=30, kde=True, color="green")
plt.title("Distribution of CAR [-10,+10] (Green Acquirers)")
plt.xlabel("CAR [-10,+10]")
plt.ylabel("Frequency")

# Adjust layout and show plot
plt.tight_layout()
plt.show()

df_filtered.to_csv("Final_Dataset.csv", index=False)
