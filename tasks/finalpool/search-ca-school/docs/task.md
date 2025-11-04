Please help me prepare a graduate application report for a student currently living in Los Angeles, California, who wishes to attend a nearby university to be able to return home regularly. Please help me find detailed information about all schools within 500 miles of the Natural History Museum of Los Angeles County that are ranked in the top 30 in USA in the CS Ranking AI field (excluding Information Retrieval) in 2024.
For each program that meets the distance requirements, please collect: 1) Complete university name, city, and ranking; 2) Shortest driving distance from the Natural History Museum of Los Angeles County (in miles, integers only); Please save the information as 'AI_univ_LA_500miles_Top30_2024.json' in the following format, sorting universities by distance from nearest to farthest, with higher-ranked universities listed first when distances are equal:

[
    {
        "university":"{name}",
        "city":"{city}",
        "cs_ranking_rank":{rank},
        "car_drive_miles":{miles}
    },
    {
        "university":"{name}",
        "city":"{city}",
        "cs_ranking_rank":{rank},
        "car_drive_miles":{miles}
    },
    ...
]