I am a travel agency staff member. I need to analyze this travel guide video（https://youtu.be/5KTSd2jGYHo）.
##Step 1: Subtitle Extraction
Extract the complete original subtitles from the provided travel guide video.
Save the subtitles as a text file with the filename format: video_subtitles.txt.
Keep the original timestamps and formatting unchanged.

##Step 2: Content Summary
Summarize only the itinerary content for the first 5 days (Day 1 to Day 5, inclusive) and save it into a markdown file.
Output strictly in the following format:

Day X: Location A → Location B → Location C

Detailed stops for the day:
- Stop 1: [Location name] - [Brief description]
- Stop 2: [Location name] - [Brief description]
- Stop 3: [Location name] - [Brief description]

Recommended visiting order: [Specific sequence with timing if available]

##Formatting Requirements:
Each day must be an independent paragraph.
If a major location includes several attractions, only the major location should be listed in the title line.
Each paragraph must begin with the format "Day X:".
Use the arrow symbol "→" consistently.
Major stops must be listed using bullet points.
The recommended visiting order must be placed on a separate line.

##Output Constraints:
All files and content must be in English.
File naming must strictly follow the specified format.
Variations in format or synonymous expressions are not allowed.
Location names must use their official names.