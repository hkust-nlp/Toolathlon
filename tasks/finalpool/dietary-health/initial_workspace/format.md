# Analysis Output Format Guide

Please follow this EXACT format for your nutritional analysis. The evaluation system will look for these specific patterns.

## Required Format:

```
# Today's Meal Nutritional Analysis

- **Carbohydrates**: [Assessment]. Expected: [range] | Actual: [calculated value]

- **Protein**: [Assessment]. Expected: [target] | Actual: [calculated value]
```

## Assessment Options:
- **Below expectations** - when actual intake is below the target range
- **Meets expectations** - when actual intake is within the target range  
- **Excessive intake** - when actual intake exceeds the target range

## Format Examples:

**Example 1:**
```
# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g
```

**Example 2:**
```
# Today's Meal Nutritional Analysis

- **Carbohydrates**: Meets expectations. Expected: 162.5g-195g | Actual: 175g

- **Protein**: Meets expectations. Expected: 97.5g | Actual: 98g
```

## Important Notes:
- Use **exactly** this heading: "# Today's Meal Nutritional Analysis"
- Include both "Expected:" and "Actual:" values
- Round numbers to 0.5g precision (e.g., 135.5g, 146.0g, 98.5g)
- Assessment must match the actual vs expected comparison
- The "|" separator between Expected and Actual is required

## Calculation Tips:
1. Extract ingredient quantities from cuisine.md
2. Look up nutritional values in Nutrition.xlsx 
3. Calculate: (nutrition per 100g / 100) × ingredient weight
4. Sum all ingredients for total daily intake
5. Compare against target ranges from health_guide.md

The evaluation system accepts approximate values within ±5g tolerance for easier agent compliance.