**BigQuery Storage Requirements:**
- Dataset: `bigquery_pricing_analysis`
- Table: `analysis`
- Full Path: `bigquery_pricing_analysis.analysis`

**BigQuery Table Structure (Required Columns):**
- `Product Name` (String) - Use the exact product name from our internal CSV file
- `Our Price` (Float) - Our product pricing
- `Competitor Price` (Float) - FutureGadget's pricing for similar products
- `Price Difference` (Float) - Calculated as (Our Price - Competitor Price)

**Data Processing Requirements:**
- Use the **Product Name** field from our internal CSV file as the standard product identifier
- Match competitor products to ours based on product features/categories
- Calculate the price difference and store these four columns accurately in the final BigQuery table.