When handling the trip planning task, you have access to the following tool capabilities:
1. **Google Maps service**: Obtain basic location and route information.
2. **Google Search**: Search for real-time transportation information, shop locations, business hours, etc.
3. **Web Scraping**: Fetch detailed webpage content, such as Google Maps detailed route pages.
4. **File System**: Save and read planning results.

## Recommended Workflow:

### 1. Geographic Location Confirmation
- Confirm the starting point (Tokyo Station Nihonbashi Exit) and the destination (Kamakura Museum of History and Culture).
- Search for the precise location and address of the "Kamakura Museum of History and Culture".

### 2. Direct Transportation Route Planning (Key Requirement)
- Search for "direct train routes from Tokyo Station to Kamakura Station" to find routes **without transfers**.
- Focus on the JR Yokosuka Line or any other direct lines.
- If a completely direct route is not available, look for options with the fewest transfers.
- Verify exit information for Kamakura Station, and select the exit best suited for reaching the museum.

### 3. Starbucks Location Search near Tokyo Station (Key Step)
- Search for "Starbucks near Tokyo Station Nihonbashi Exit".
- Give priority to Starbucks inside Tokyo Station or in the Marunouchi area.
- Obtain the exact address, business hours, and walking distance from the Nihonbashi Exit.
- **Choose the Starbucks closest to the Nihonbashi Exit**.

### 4. Kamakura Detailed Information Supplement
- Search for the museum's opening hours and ticket information.
- Obtain a detailed walking route and duration from Kamakura Station to the museum.

### 5. Information Integration
- Consolidate all information into the required JSON format.
- **Important**: All JSON content must use English output.
- **Important**: Add a `summary_route` field, formatted as: "Tokyo Station (Nihonbashi Exit) → [train line] → Kamakura Station ([exit]) + [walking duration] + [Starbucks store name]".
- Save as the travel_plan.json file.

## Special Notes:
- **Direct Route Priority**: The user clearly prefers a direct route with no transfers; always prioritize a direct or minimum-transfer route.
- **Starbucks Selection at Tokyo Station**: Focus on finding the closest Starbucks inside Tokyo Station, not at Kamakura Station.
- **English Output Required**: All JSON field values must be in English, including place names and activity descriptions.
- **Concise JSON Format**: Include only core information; focus on practical trip planning data.
- **Simplified Information**: Focus on practical travel information, technical data like coordinates are not needed.
- Cross-validate information using multiple tools when necessary.
- If you need to save the file and the user provides a relative path, combine it with the workspace directory for the complete path.

If you believe the trip planning task is complete and travel_plan.json has been saved, you may use the done tool to declare the task finished.