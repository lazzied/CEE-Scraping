"""
workflow:
each year: contains two 3 paages: the main page, the exam page and the solution page

the exam and solution page have pratically the same format, so basically we need to build two dom trees: one for the main page, one for the exam/solution page and each has their own variation/inconsistencies
i should have an error detection when the DOM structure changes, so that i can update the blueprints accordingly

checked: also the number of subjects can vary, so the json blueprint must be dynamic enough to handle that : so when you encounter the count="auto" you look for the number of children available in the actual page and build accordingly
we need to cache the blueprints for each page structure, so that we can reuse them when needed

scraping steps:
first we will test the sequential way, we'll explore parallelization later if needed
1. load main page
2. build dom tree for main page based on blueprint
3. for each examType in examTypeContainer:
    - locate container for examType
    - extract type_text and year
    - get subject elements
    - for each subject element:
        - extract subject name
        - build dom tree for subject based on blueprint
        - for each exam variant in subject:
            - extract exam variant info
            - navigate to exam page
            - build dom tree for exam page based on blueprint
            - scrape exam data
            - navigate to solution page
            - build dom tree for solution page based on blueprint
            - scrape solution data
            - store data in database
locating is easy, they are predetermined by the node descriptions/ tag/ id/ classes etc... in the json blueprint, so we just need to find the it collect the infos and move on to the next node

for annotation, we use the shortest path to a landmark; we don't always use the root's node to find the web element, sometimes we use a parent node as the base to find child nodes, this is more efficient and less error-prone
also we don't need to compare all the landmarks, like the sti range from 1 to 33, they are all landmarks, we compare parents/ grandparents/ cousins/uncles etc... then we compare the distance to the target node, this way we can find the target node more accurately
"""