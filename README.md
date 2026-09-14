# UniPlan – SI University Scheduler

## M603A Advanced Algorithms Project

**Student:** Saadiya Shaikh  
**Student ID:** GH1019657  
**University:** GISMA University of Applied Sciences  

## Overview

UniPlan is a university timetable scheduling system that uses multiple algorithms to create a valid schedule while reducing room capacity waste.

### Algorithms Used

- Greedy Scheduling
- Conflict Graph
- Welsh–Powell Graph Colouring
- Dynamic Programming for Room Optimisation
- Recursive Backtracking Repair
- Schedule Validation

### Dataset

- 5,000 students
- 300 professors
- 50 rooms
- 5 campuses
- 1,366 classes
- 1,550 required sessions

Dataset: `data/SI_University_Scheduling_Dataset_AUDITED_FINAL.xlsx`

### Run the Project

```bash
python src/main.py

Run the web application:

python src/app.py

Open:

[http://**127**.0.0.1:**5001**](http://**127**.0.0.1:**5001**) ### Final Results 1,**550** / 1,**550** sessions scheduled 0 failed classes 0 professor conflicts 0 student group conflicts 0 room conflicts 0 capacity errors 59.86% room utilisation 79.81% campus match
79.81% campus match
