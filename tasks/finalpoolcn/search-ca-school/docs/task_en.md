Please help me prepare a graduate school application report for a student currently residing in Los Angeles, CA, who wishes to attend a local university to return home regularly. Please help me find detailed information on all computer science graduate programs within 500 miles of the Natural History Museum of Los Angeles County among the Top 30 US Computer Science Graduate Programs according to US News 2025 rankings.
For each program that meets the distance requirements, please collect: 1) Complete university name, city, and ranking; 2) Shortest driving distance from the Natural History Museum of Los Angeles County (in miles, integers only); Please save the information as 'cs_masters_LA_500miles_Top30_2025.json' in the following format, sorting universities by distance from nearest to farthest, with higher-ranked universities listed first when distances are equal:

[
    {
        "university":"{name}",
        "city":"{city}",
        "usnews_cs_ranking":{rank},
        "car_drive_miles":{miles}
    },
    {
        "university":"{name}",
        "city":"{city}",
        "usnews_cs_ranking":{rank},
        "car_drive_miles":{miles}
    },
    ...
]