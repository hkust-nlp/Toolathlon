## Project Overview

This project connects to a Formula 1 database in a Kubernetes cluster using secure port forwarding and executes SQL queries to analyze historical Formula 1 data. The goal is to identify the top-scoring driver and constructor for each year from 1950 to 2024, then output the results to a CSV file.

---

## 1. Data Sources

* **F1 Database**: MySQL database named "f1" running in the `data` namespace of the Kubernetes cluster, containing comprehensive Formula 1 historical data including drivers, constructors, races, and results.

* **Database Access**: Read-only database account with credentials:
  * Username: `reader`
  * Password: `mcpbench0606`

* **Secure Connection**: Database access is established through Kubernetes port forwarding to ensure secure connectivity without exposing the database directly.

---

## 2. Query Requirements

### Target Analysis

* **Objective**: For each year from 1950 to 2024, identify:
  * The driver who scored the most points
  * The constructor who scored the most points
  * Full driver names (not abbreviated)

### Database Query Structure

The analysis requires joining multiple tables to correlate:
* **Years**: Racing seasons from 1950-2024
* **Drivers**: Full driver names and their point totals per year
* **Constructors**: Constructor/team names and their point totals per year
* **Results**: Race results and points awarded

### Output Format

Results must be saved to `results.csv` with exactly three columns:

| year | driver | constructor |
|------|--------|-------------|
| 1950 | Nino Farina | Alfa Romeo |
| 1951 | Juan Fangio | Ferrari |
| ... | ... | ... |

---

## 3. GT Solution Acquisition

The ground truth (GT) solution is stored in `evaluation/gt.csv` and contains the expected results for all years from 1950 to 2024.

1. **GT Data Structure**: The ground truth file contains 77 rows (including header) covering:
   * **Historical Era** (1950s-1960s): Early Formula 1 champions like Fangio, Ascari
   * **Classic Era** (1970s-1980s): Icons like Stewart, Lauda, Prost
   * **Modern Era** (1990s-2000s): Schumacher, Hkkinen, Hamilton dominance
   * **Current Era** (2010s-2024): Vettel, Hamilton, Verstappen championships

2. **Evaluation Process**:
   ```python
   # The evaluation system:
   # 1. Compares agent-generated results.csv with gt.csv
   csv_match = compare_csv(gt_path, target_file)
   
   # 2. Performs row-by-row comparison with flexible matching:
   # - Year: Strict string matching
   # - Driver: Case-insensitive, ignores whitespace and quotes  
   # - Constructor: Case-insensitive, ignores whitespace and quotes
   ```

3. **Key GT Examples**:
   * **1950**: Nino Farina (driver) + Alfa Romeo (constructor)
   * **1988**: Alain Prost (driver) + McLaren (constructor) 
   * **2024**: Max Verstappen (driver) + McLaren (constructor)

4. **Validation Requirements**:
   * All 77 years must be present in the results
   * Driver names must be complete (full names, not initials)
   * Constructor names must match historical records
   * CSV format must exactly match the template structure

The GT solution validates that the agent successfully connects to the database, writes appropriate SQL queries to aggregate points by year, and formats the output correctly for all Formula 1 seasons.