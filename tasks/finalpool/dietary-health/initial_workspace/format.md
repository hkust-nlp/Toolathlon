# Analysis Output Format Guide

Please follow this EXACT format for your nutritional analysis.

## Required Format:

```
# Today's Meal Nutritional Analysis

- **Carbohydrates**: [Assessment]. Expected: [range] | Actual: [calculated value]

- **Protein**: [Assessment]. Expected: [target] | Actual: [calculated value]
```

## Assessment Options:
- **Below expectations** -  the actual intake is under 95% of the lower bound of the target range
- **Excessive intake** - the actual intake is over 105% of the upper bound of the target range
- **Meets expectations** - otherwise

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
- The "|" separator between Expected and Actual is required
- Use the average nutrient value when the ingredient amount is provided as a range