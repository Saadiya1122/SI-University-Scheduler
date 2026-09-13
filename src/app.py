from flask import Flask, render_template, request, jsonify
import pandas as pd
import os
import json
import shutil
import tempfile
from datetime import timedelta
import ast
from werkzeug.utils import secure_filename
from validator import validate_schedule, validate_dataset
from data_loader import get_schedule_config
from main import run as generate_schedule

app = Flask(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SCHEDULE_FILE = os.path.join(PROJECT_ROOT, "output", "final_schedule.csv")
DATASET_FILE = os.path.join(PROJECT_ROOT, "data","SI_University_Scheduling_Dataset_AUDITED_FINAL.xlsx")

PREFERENCES_FILE = os.path.join(PROJECT_ROOT,"data","professor_preferences.json")

def load_schedule():
    if not os.path.exists(SCHEDULE_FILE):
        raise FileNotFoundError(f"Schedule file not found: {SCHEDULE_FILE}")

    return pd.read_csv(SCHEDULE_FILE)


def load_dataset():
    if not os.path.exists(DATASET_FILE):
        raise FileNotFoundError(f"Dataset file not found: {DATASET_FILE}")

    return pd.read_excel(DATASET_FILE, sheet_name=None)


def load_professor_preferences():
    if not os.path.exists(PREFERENCES_FILE):
        return {}
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

def save_professor_preferences(preferences):
    os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)

    with open(PREFERENCES_FILE, "w", encoding="utf-8") as file:
        json.dump(preferences, file, indent=4, ensure_ascii=False)


def calculate_metrics(schedule_df, dataset):
    quarters = {}

    for quarter in ["Q1", "Q2", "Q3", "Q4"]:
        quarter_df = schedule_df[schedule_df["quarter_id"] == quarter]

        if len(quarter_df) > 0:
            total_students = pd.to_numeric(
                quarter_df["student_count"], errors="coerce").fillna(0).sum()

            total_capacity = pd.to_numeric(
                quarter_df["capacity"], errors="coerce").fillna(0).sum()

            if total_capacity > 0:
                utilization = total_students / total_capacity * 100
            else:
                utilization = 0

            campus_matches = (
                quarter_df["campus_id"].astype(str).str.strip()
                == quarter_df["room_campus_id"].astype(str).str.strip()).sum()

            campus_match = campus_matches / len(quarter_df) * 100
        else:
            utilization = 0
            campus_match = 0

        quarters[quarter] = {"sessions": len(quarter_df), "utilization": round(utilization, 2),"campus_match": round(campus_match, 2)}

    schedule_students = pd.to_numeric(schedule_df["student_count"], errors="coerce").fillna(0).sum()

    schedule_capacity = pd.to_numeric(schedule_df["capacity"], errors="coerce").fillna(0).sum()

    if schedule_capacity > 0:
        overall_utilization = schedule_students / schedule_capacity * 100
    else:
        overall_utilization = 0

    if len(schedule_df) > 0:
        overall_campus_matches = (
            schedule_df["campus_id"].astype(str).str.strip()
            == schedule_df["room_campus_id"].astype(str).str.strip()).sum()

        overall_campus_match = (
            overall_campus_matches / len(schedule_df) * 100)
    else:
        overall_campus_match = 0

    expected_sessions = 0

    if "classes" in dataset:
        classes_df = dataset["classes"]

        if "sessions_per_week" in classes_df.columns:
            expected_sessions = int(pd.to_numeric(classes_df["sessions_per_week"],errors="coerce").fillna(0).sum())

    scheduled_sessions = len(schedule_df)

    if expected_sessions > 0:
        session_completion = scheduled_sessions / expected_sessions * 100
    else:
        session_completion = 0

    return {
        "quarters": quarters,
        "room_utilization": round(overall_utilization, 2),
        "campus_match": round(overall_campus_match, 2),
        "scheduled_sessions": scheduled_sessions,
        "expected_sessions": expected_sessions,
        "session_completion": round(session_completion, 2)}


def create_professor_map():
    data = load_dataset()
    professors = data["professors"]
    professor_map = {}

    for _, professor in professors.iterrows():
        professor_id = str(professor.get("professor_id", "")).strip()
        title = str(professor.get("title", "")).strip()
        first_name = str(professor.get("first_name", "")).strip()
        last_name = str(professor.get("last_name", "")).strip()

        full_name = f"{title} {first_name} {last_name}".strip()
        professor_map[professor_id] = full_name

    return professor_map


def build_calendar_weeks(data):
    calendar = data["academic_calendar"]
    exceptions = data["calendar_exceptions"]
    closures = []

    for _, exception in exceptions.iterrows():
        start = pd.to_datetime(exception["start_date"]).date()
        end = pd.to_datetime(exception["end_date"]).date()
        closures.append((start, end))

    result = {}

    for _, quarter in calendar.iterrows():
        quarter_id = str(quarter["quarter_id"]).strip()

        quarter_start = pd.to_datetime(
            quarter["quarter_start_date"]).date()

        quarter_end = pd.to_datetime(
            quarter["quarter_end_date"]).date()

        weeks = []

        current_monday = quarter_start - timedelta(
            days=quarter_start.weekday())

        week_number = 1

        while current_monday <= quarter_end:
            current_friday = current_monday + timedelta(days=4)
            week_has_closure = False

            for closure_start, closure_end in closures:
                if (current_monday <= closure_end and current_friday >= closure_start):
                    week_has_closure = True
                    break

            if not week_has_closure:
                actual_start = max(current_monday, quarter_start)
                actual_end = min(current_friday, quarter_end)

                weeks.append({
                    "week": week_number,
                    "start": actual_start.isoformat(),
                    "end": actual_end.isoformat(),
                    "start_display": actual_start.strftime("%d %b %Y"),
                    "end_display": actual_end.strftime("%d %b %Y")
                })

                week_number += 1

            current_monday += timedelta(days=7)

        result[quarter_id] = weeks

    return result


@app.route("/")
def home():
    schedule_df = load_schedule()
    dataset = load_dataset()
    schedule_config = get_schedule_config(dataset)
    interval_minutes = schedule_config["scheduling_interval_minutes"]

    metrics = calculate_metrics(schedule_df, dataset)

    if "students" in dataset:
        students_count = len(dataset["students"])
    else:
        students_count = 0

    if "classes" in dataset:
        if "class_id" in dataset["classes"].columns:
            classes_count = dataset["classes"]["class_id"].nunique()
        else:
            classes_count = len(dataset["classes"])
    else:
        classes_count = 0

    if "professors" in dataset:
        professors_count = len(dataset["professors"])
    else:
        professors_count = 0

    data = {
        "students": students_count,
        "classes": classes_count,
        "sessions": metrics["scheduled_sessions"],
        "professors": professors_count,
        "quarters": metrics["quarters"],
        "performance": {
            "room_utilization": metrics["room_utilization"],
            "campus_match": metrics["campus_match"],
            "session_completion": metrics["session_completion"]
        }
    }

    return render_template("index.html", data=data)

@app.route("/timetable")
def timetable():
    df = load_schedule()
    professor_map = create_professor_map()
    schedule = []

    for _, row in df.iterrows():
        session = row.to_dict()

        professor_id = str(
            session.get("professor_id", "")).strip()

        session["professor_name"] = professor_map.get(
            professor_id,
            professor_id)

        schedule.append(session)

    dataset = load_dataset()

    campuses = dataset["campuses"].to_dict("records")
    schedule_config = get_schedule_config(dataset)
    calendar_weeks = build_calendar_weeks(dataset)

    return render_template(
        "timetable.html",
        schedule=schedule,
        calendar_weeks=calendar_weeks,
        schedule_config=schedule_config,
        campuses=campuses)


@app.route("/professors")
def professors():
    schedule_df = load_schedule()
    dataset = load_dataset()
    professors_df = dataset["professors"].copy()
    professors_list = []

    for _, professor in professors_df.iterrows():
        professor_id = str(professor.get("professor_id", "")).strip()

        title = str(professor.get("title", "")).strip()
        first_name = str(professor.get("first_name", "")).strip()

        last_name = str(professor.get("last_name", "")).strip()

        faculty_id = str(professor.get("faculty_id", "")).strip()

        campus_id = str(professor.get("primary_campus_id", "")).strip()

        full_name = f"{title} {first_name} {last_name}".strip()

        professors_list.append({
            "professor_id": professor_id,
            "name": full_name,
            "faculty_id": faculty_id,
            "campus_id": campus_id,
            "session_count": 0})

    if "professor_id" in schedule_df.columns:
        session_counts = (
            schedule_df["professor_id"]
            .astype(str)
            .str.strip()
            .value_counts()
            .to_dict()
        )
    else:
        session_counts = {}

    for professor in professors_list:
        professor["session_count"] = session_counts.get(professor["professor_id"],0)

    sessions_by_professor = {}

    for _, row in schedule_df.iterrows():
        professor_id = str(row.get("professor_id", "")).strip()

        if professor_id not in sessions_by_professor:
            sessions_by_professor[professor_id] = []

        sessions_by_professor[professor_id].append({
            "quarter_id": row.get("quarter_id", ""),
            "class_id": row.get("class_id", ""),
            "module_name": row.get("module_name", ""),
            "programme_name": row.get("programme_name", ""),
            "day": row.get("day", ""),
            "start_time": row.get("start_time", ""),
            "duration_hours": row.get("duration_hours", ""),
            "room_id": row.get("room_id", ""),
            "campus_id": row.get("campus_id", "")
        })

    return render_template(
        "professors.html",
        professors=professors_list,
        sessions_by_professor=sessions_by_professor)

@app.route("/preferences")
def preferences():
    dataset = load_dataset()
    professors_df = dataset["professors"].copy()
    professors_list = []

    for _, professor in professors_df.iterrows():
        professor_id = str(professor.get("professor_id", "")).strip()

        title = str(professor.get("title", "")).strip()
        first_name = str(professor.get("first_name", "")).strip()

        last_name = str(professor.get("last_name", "")).strip()

        full_name = f"{title} {first_name} {last_name}".strip()

        professors_list.append({"professor_id": professor_id,"name": full_name})

    preferences = load_professor_preferences()

    return render_template(
        "preferences.html",
        professors=professors_list,
        professor_preferences=preferences)


@app.route("/api/preferences", methods=["POST"])
def save_preferences():
    try:
        payload = request.get_json()

        if not payload:
            return jsonify({
                "success": False,
                "message": "No data received."
            }), 400

        professor_id = str(payload.get("professor_id", "")).strip()

        if not professor_id:
            return jsonify({"success": False,"message": "Professor ID is required."}), 400

        preferences = load_professor_preferences()

        preferences[professor_id] = {
            "availability": payload.get("availability", {}),
            "preferred_time": payload.get("preferred_time", "none"),
            "preferred_days": payload.get("preferred_days", []),
            "prefer_fewer_gaps": bool(payload.get("prefer_fewer_gaps", False)),
            "prefer_fewer_days": bool(payload.get("prefer_fewer_days", False)),
            "notes": str(payload.get("notes", ""))
        }

        save_professor_preferences(preferences)

        return jsonify({"success": True,"message": "Preferences saved successfully."})

    except Exception as error:
        return jsonify({"success": False,"message": str(error)}), 500


@app.route("/rooms")
def rooms():
    schedule_df = load_schedule()
    dataset = load_dataset()
    rooms_df = dataset["rooms"].copy()
    buildings_df = dataset["buildings"].copy()

    building_map = {}

    for _, building in buildings_df.iterrows():
        building_id = str(building.get("building_id", "")).strip()

        building_name = str(building.get("building_name", "")).strip()

        campus_id = str(building.get("campus_id", "")).strip()

        building_map[building_id] = {"building_name": building_name,"campus_id": campus_id}

    rooms_list = []

    for _, room in rooms_df.iterrows():
        room_id = str(room.get("room_id", "")).strip()
        building_id = str(room.get("building_id", "")).strip()

        building = building_map.get(building_id, {})

        building_name = building.get("building_name",building_id)

        campus_id = building.get("campus_id", "")

        capacity = pd.to_numeric(room.get("capacity", 0),errors="coerce")

        if pd.isna(capacity):
            capacity = 0

        room_schedule = schedule_df[schedule_df["room_id"].astype(str).str.strip() == room_id]

        if len(room_schedule) > 0:
            students = pd.to_numeric(room_schedule["student_count"],errors="coerce").fillna(0).sum()

            assigned_capacity = pd.to_numeric(room_schedule["capacity"],errors="coerce").fillna(0).sum()

            session_count = len(room_schedule)

            if session_count > 0:
                average_students = students / session_count
            else:
                average_students = 0

            if assigned_capacity > 0:
                utilization = students / assigned_capacity * 100
            else:
                utilization = 0
        else:
            session_count = 0
            average_students = 0
            utilization = 0

        rooms_list.append({
            "room_id": room_id,
            "capacity": int(capacity),
            "building_name": building_name,
            "campus_id": campus_id,
            "room_type": str(
                room.get("room_type", "")
            ).strip(),
            "session_count": session_count,
            "average_students": round(average_students, 1),
            "utilization": round(utilization, 2)
        })

    rooms_list.sort(key=lambda room: room["room_id"])

    return render_template("rooms.html", rooms=rooms_list)


@app.route("/campuses")
def campuses():
    schedule_df = load_schedule()
    dataset = load_dataset()
    campuses_df = dataset["campuses"].copy()
    buildings_df = dataset["buildings"].copy()

    building_counts = (
        buildings_df["campus_id"]
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )

    campuses_list = []

    for _, campus in campuses_df.iterrows():
        campus_id = str(campus.get("campus_id", "")).strip()

        campus_name = str(campus.get("campus_name", "")).strip()

        city = str(campus.get("city", "")).strip()
        district = str(campus.get("district", "")).strip()

        room_count = pd.to_numeric(campus.get("room_count", 0),errors="coerce")

        total_capacity = pd.to_numeric(campus.get("total_capacity", 0),errors="coerce")

        if pd.isna(room_count):
            room_count = 0

        if pd.isna(total_capacity):
            total_capacity = 0

        campus_schedule = schedule_df[schedule_df["room_campus_id"].astype(str).str.strip()== campus_id]

        session_count = len(campus_schedule)

        if session_count > 0:
            students = pd.to_numeric(campus_schedule["student_count"],errors="coerce").fillna(0).sum()

            assigned_capacity = pd.to_numeric(campus_schedule["capacity"],errors="coerce").fillna(0).sum()

            campus_matches = (campus_schedule["campus_id"].astype(str).str.strip()== campus_schedule["room_campus_id"].astype(str).str.strip()).sum()

            campus_match = campus_matches / session_count * 100

            if assigned_capacity > 0:
                utilization = students / assigned_capacity * 100
            else:
                utilization = 0
        else:
            campus_match = 0
            utilization = 0

        campuses_list.append({
            "campus_id": campus_id,
            "campus_name": campus_name,
            "city": city,
            "district": district,
            "building_count": building_counts.get(campus_id, 0),
            "room_count": int(room_count),
            "total_capacity": int(total_capacity),
            "session_count": session_count,
            "campus_match": round(campus_match, 2),
            "utilization": round(utilization, 2)
        })

    total_campuses = len(campuses_list)

    total_rooms = sum(campus["room_count"]for campus in campuses_list)

    total_capacity = sum(campus["total_capacity"] for campus in campuses_list)

    total_sessions = len(schedule_df)

    if total_sessions > 0:
        total_matches = (schedule_df["campus_id"].astype(str).str.strip() == schedule_df["room_campus_id"].astype(str).str.strip()).sum()

        overall_campus_match = total_matches / total_sessions * 100
    else:
        overall_campus_match = 0

    campuses_list.sort(key=lambda campus: campus["campus_id"])

    return render_template(
        "campuses.html",
        campuses=campuses_list,
        total_campuses=total_campuses,
        total_rooms=total_rooms,
        total_capacity=total_capacity,
        total_sessions=total_sessions,
        overall_campus_match=round(overall_campus_match, 2)
    )


@app.route("/analytics")
def analytics():
    schedule_df = load_schedule()
    dataset = load_dataset()

    metrics = calculate_metrics(schedule_df,dataset)

    total_students = pd.to_numeric(schedule_df["student_count"],errors="coerce").fillna(0).sum()

    total_capacity = pd.to_numeric(
        schedule_df["capacity"],
        errors="coerce"
    ).fillna(0).sum()

    rooms_used = (
        schedule_df["room_id"]
        .astype(str)
        .str.strip()
        .nunique()
    )

    total_rooms = len(dataset["rooms"])

    if total_rooms > 0:
        room_usage_rate = rooms_used / total_rooms * 100
    else:
        room_usage_rate = 0

    quarter_data = []

    for quarter in ["Q1", "Q2", "Q3", "Q4"]:
        quarter_metrics = metrics["quarters"].get(
            quarter,
            {
                "sessions": 0,
                "utilization": 0,
                "campus_match": 0
            }
        )

        quarter_data.append({
            "quarter": quarter,
            "sessions": quarter_metrics["sessions"],
            "utilization": quarter_metrics["utilization"],
            "campus_match": quarter_metrics["campus_match"]
        })

    campus_data = []

    for _, campus in dataset["campuses"].iterrows():
        campus_id = str(
            campus.get("campus_id", "")
        ).strip()

        campus_name = str(
            campus.get("campus_name", campus_id)
        ).strip()

        campus_schedule = schedule_df[
            schedule_df["room_campus_id"].astype(str).str.strip()
            == campus_id
        ]

        campus_sessions = len(campus_schedule)

        campus_data.append({
            "campus_id": campus_id,
            "campus_name": campus_name,
            "sessions": campus_sessions
        })

    algorithm_results_file = os.path.join(
        PROJECT_ROOT,
        "output",
        "algorithm_results.json"
    )

    algorithm_data = []

    if os.path.exists(algorithm_results_file):
        try:
            with open(
                algorithm_results_file,
                "r",
                encoding="utf-8"
            ) as file:
                algorithm_data = json.load(file)
        except (json.JSONDecodeError, OSError):
            algorithm_data = []

    best_utilization_quarter = max(
        quarter_data,
        key=lambda item: item["utilization"]
    )

    best_campus_match_quarter = max(
        quarter_data,
        key=lambda item: item["campus_match"]
    )

    return render_template(
        "analytics.html",
        room_utilization=metrics["room_utilization"],
        campus_match=metrics["campus_match"],
        session_completion=metrics["session_completion"],
        scheduled_sessions=metrics["scheduled_sessions"],
        expected_sessions=metrics["expected_sessions"],
        total_students=int(total_students),
        total_capacity=int(total_capacity),
        rooms_used=rooms_used,
        total_rooms=total_rooms,
        room_usage_rate=round(room_usage_rate, 2),
        quarter_data=quarter_data,
        campus_data=campus_data,
        algorithm_data=algorithm_data,
        best_utilization_quarter=best_utilization_quarter,
        best_campus_match_quarter=best_campus_match_quarter
    )


@app.route("/conflicts")
def conflicts():
    schedule_df = load_schedule()
    dataset = load_dataset()
    schedule_config = get_schedule_config(dataset)

    interval_minutes = schedule_config[
        "scheduling_interval_minutes"
    ]

    def time_to_minutes(value):
        text = str(value).strip()
        parts = text.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        return hour * 60 + minute

    def build_blocks(start_time, duration_hours):
        start_minutes = time_to_minutes(start_time)
        duration_minutes = float(duration_hours) * 60
        block_count = int(duration_minutes / interval_minutes)
        blocks = []

        for index in range(block_count):
            block_start = start_minutes + index * interval_minutes
            hour = block_start // 60
            minute = block_start % 60
            blocks.append(f"{hour:02d}:{minute:02d}")

        return blocks

    classes_df = dataset["classes"].copy()
    quarter_modules_df = dataset["quarter_modules"].copy()

    class_quarter_df = classes_df.merge(
        quarter_modules_df[
            ["quarter_module_id", "quarter_id"]
        ],
        on="quarter_module_id",
        how="left"
    )
    
    modules_df = dataset["modules"].copy()

    assigned_module_ids = set(
        quarter_modules_df["module_id"].dropna().astype(str).str.strip()
    )

    unassigned_modules = modules_df[
        ~modules_df["module_id"].astype(str).str.strip().isin(assigned_module_ids)
    ].copy()

    unassigned_modules = unassigned_modules[
        ["module_id", "module_code", "module_name"]
    ].to_dict("records")

    schedule_records = []

    for _, row in schedule_df.iterrows():
        record = row.to_dict()

        record["class_id"] = str(record.get("class_id", "")).strip()

        record["professor_id"] = str(record.get("professor_id", "")).strip()

        record["day"] = str(record.get("day", "")).strip()

        record["room_id"] = str(record.get("room_id", "")).strip()

        record["quarter_id"] = str(record.get("quarter_id", "")).strip()

        value = record.get("group_ids", "")

        if isinstance(value, list):
            groups = [
                str(item).strip()
                for item in value
            ]
        elif pd.isna(value):
            groups = []
        else:
            text = str(value).strip()

            try:
                parsed = ast.literal_eval(text)

                if isinstance(parsed, (list, tuple, set)):
                    groups = [
                        str(item).strip()
                        for item in parsed
                    ]
                else:
                    groups = [
                        item.strip()
                        for item in text.split(",")
                        if item.strip()
                    ]
            except (ValueError, SyntaxError):
                groups = [
                    item.strip()
                    for item in text.split(",")
                    if item.strip()
                ]

        record["group_ids"] = groups

        record["blocks"] = build_blocks(
            record["start_time"],
            record["duration_hours"]
        )

        schedule_records.append(record)

    quarters = ["Q1", "Q2", "Q3", "Q4"]

    professor_conflicts = 0
    group_conflicts = 0
    room_conflicts = 0
    capacity_errors = 0
    session_errors = 0

    quarter_results = []

    for quarter in quarters:
        quarter_schedule = [
            record
            for record in schedule_records
            if record.get("quarter_id", "") == quarter
        ]

        quarter_classes_df = class_quarter_df[
            class_quarter_df["quarter_id"].astype(str).str.strip()
            == quarter
        ]

        quarter_classes = []

        for _, row in quarter_classes_df.iterrows():
            quarter_classes.append({
                "class_id": str(
                    row["class_id"]
                ).strip(),
                "sessions_per_week": int(
                    pd.to_numeric(
                        row["sessions_per_week"],
                        errors="coerce"
                    )
                )
            })

        report = validate_schedule(
            quarter_schedule,
            quarter_classes
        )

        professor_conflicts += report["professor_conflicts"]
        group_conflicts += report["group_conflicts"]
        room_conflicts += report["room_conflicts"]
        capacity_errors += report["capacity_errors"]
        session_errors += report["session_errors"]

        quarter_results.append({
            "quarter": quarter,
            "valid": report["valid"],
            "professor_conflicts": report["professor_conflicts"],
            "group_conflicts": report["group_conflicts"],
            "room_conflicts": report["room_conflicts"],
            "capacity_errors": report["capacity_errors"],
            "session_errors": report["session_errors"]
        })

    failed_classes = []

    actual_session_counts = (
        schedule_df["class_id"]
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )

    for _, row in class_quarter_df.iterrows():
        class_id = str(row["class_id"]).strip()

        expected = int(
            pd.to_numeric(
                row["sessions_per_week"],
                errors="coerce"
            )
        )

        actual = int(
            actual_session_counts.get(class_id, 0)
        )

        if actual != expected:
            failed_classes.append({
                "class_id": class_id,
                "quarter": str(
                    row["quarter_id"]
                ).strip(),
                "expected": expected,
                "actual": actual,
                "reason": "Missing or incomplete sessions"
            })

    total_conflicts = (
        professor_conflicts
        + group_conflicts
        + room_conflicts
        + capacity_errors
        + session_errors
    )

    schedule_valid = total_conflicts == 0
    conflict_rows = []

    for quarter in quarters:
        quarter_records = [
            record
            for record in schedule_records
            if record.get("quarter_id", "") == quarter
        ]

        for i in range(len(quarter_records)):
            a = quarter_records[i]

            for j in range(i + 1, len(quarter_records)):
                b = quarter_records[j]

                if a["class_id"] == b["class_id"]:
                    continue

                if a["day"] != b["day"]:
                    continue

                if not (set(a["blocks"]) & set(b["blocks"])):
                    continue

                if (
                    a["professor_id"]
                    and a["professor_id"] == b["professor_id"]
                ):
                    conflict_rows.append({
                        "type": "Professor",
                        "class_a": a["class_id"],
                        "class_b": b["class_id"],
                        "quarter": quarter,
                        "day": a["day"],
                        "time": f"{a['start_time']} – {b['start_time']}",
                        "entity": a["professor_id"]
                    })

                shared_groups = (
                    set(a["group_ids"])
                    & set(b["group_ids"])
                )

                if shared_groups:
                    conflict_rows.append({
                        "type": "Student Group",
                        "class_a": a["class_id"],
                        "class_b": b["class_id"],
                        "quarter": quarter,
                        "day": a["day"],
                        "time": f"{a['start_time']} – {b['start_time']}",
                        "entity": ", ".join(sorted(shared_groups))
                    })

                if (
                    a["room_id"]
                    and a["room_id"] == b["room_id"]
                ):
                    conflict_rows.append({
                        "type": "Room",
                        "class_a": a["class_id"],
                        "class_b": b["class_id"],
                        "quarter": quarter,
                        "day": a["day"],
                        "time": f"{a['start_time']} – {b['start_time']}",
                        "entity": a["room_id"]
                    })

    return render_template(
        "conflicts.html",
        total_conflicts=total_conflicts,
        professor_conflicts=professor_conflicts,
        group_conflicts=group_conflicts,
        room_conflicts=room_conflicts,
        capacity_errors=capacity_errors,
        session_errors=session_errors,
        failed_classes=failed_classes,
        conflict_rows=conflict_rows,
        quarter_results=quarter_results,
        schedule_valid=schedule_valid,
        unassigned_modules=unassigned_modules
    )


@app.route("/api/data-management/status", methods=["GET"])
def data_management_status():
    try:
        dataset = load_dataset()

        return jsonify({
            "success": True,
            "filename": os.path.basename(DATASET_FILE),
            "valid": validate_dataset(dataset),
            "students": len(dataset.get("students", [])),
            "classes": len(dataset.get("classes", [])),
            "professors": len(dataset.get("professors", [])),
            "rooms": len(dataset.get("rooms", [])),
            "campuses": len(dataset.get("campuses", []))
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route("/api/data-management/upload", methods=["POST"])
def upload_dataset():
    uploaded_file = request.files.get("dataset")

    if uploaded_file is None:
        return jsonify({
            "success": False,
            "message": "No dataset file was uploaded."
        }), 400

    if not uploaded_file.filename:
        return jsonify({
            "success": False,
            "message": "Please select an Excel file."
        }), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename.lower().endswith(".xlsx"):
        return jsonify({
            "success": False,
            "message": "Only .xlsx Excel files are supported."
        }), 400

    data_directory = os.path.dirname(DATASET_FILE)
    os.makedirs(data_directory, exist_ok=True)

    temporary_file = None

    dataset_backup = DATASET_FILE + ".backup"
    schedule_backup = SCHEDULE_FILE + ".backup"

    conflict_report = os.path.join(
        PROJECT_ROOT,
        "output",
        "conflict_report.csv"
    )

    conflict_backup = conflict_report + ".backup"

    algorithm_results_file = os.path.join(PROJECT_ROOT,"output","algorithm_results.json")

    algorithm_backup = algorithm_results_file + ".backup"

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".xlsx",
            dir=data_directory
        ) as temp_file:
            temporary_file = temp_file.name

        uploaded_file.save(temporary_file)

        uploaded_data = pd.read_excel(
            temporary_file,
            sheet_name=None
        )

        if not validate_dataset(uploaded_data):
            return jsonify({
                "success": False,
                "message": (
                    "The dataset could not be activated. "
                    "The previous dataset and schedule were restored. "
                    f"Error: {error}"
                )
            }), 400

        if os.path.exists(DATASET_FILE):
            shutil.copy2(DATASET_FILE, dataset_backup)

        if os.path.exists(SCHEDULE_FILE):
            shutil.copy2(SCHEDULE_FILE, schedule_backup)

        if os.path.exists(conflict_report):
            shutil.copy2(conflict_report, conflict_backup)

        if os.path.exists(algorithm_results_file):
            shutil.copy2(algorithm_results_file, algorithm_backup)

        os.replace(temporary_file, DATASET_FILE)
        temporary_file = None

        if os.path.exists(SCHEDULE_FILE):
            os.remove(SCHEDULE_FILE)

        if os.path.exists(conflict_report):
            os.remove(conflict_report)

        if os.path.exists(algorithm_results_file):
            os.remove(algorithm_results_file)

        generate_schedule()

        return jsonify({
            "success": True,
            "message": "Dataset uploaded and schedule regenerated successfully."
        })

    except Exception as error:
        if os.path.exists(DATASET_FILE) and os.path.exists(dataset_backup):
            os.replace(dataset_backup, DATASET_FILE)

        if os.path.exists(schedule_backup):
            os.replace(schedule_backup, SCHEDULE_FILE)

        if os.path.exists(conflict_backup):
            os.replace(conflict_backup, conflict_report)

        if os.path.exists(algorithm_backup):
            os.replace(algorithm_backup, algorithm_results_file)

        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        if temporary_file and os.path.exists(temporary_file):
            os.remove(temporary_file)

        for backup_file in [
            dataset_backup,
            schedule_backup,
            conflict_backup,
            algorithm_backup
        ]:
            if os.path.exists(backup_file):
                try:
                    os.remove(backup_file)
                except OSError:
                    pass


@app.route("/settings")
def settings():
    schedule_df = load_schedule()
    dataset = load_dataset()

    metrics = calculate_metrics(
        schedule_df,
        dataset
    )

    system_info = {
        "students": len(dataset["students"]),
        "classes": len(dataset["classes"]),
        "professors": len(dataset["professors"]),
        "rooms": len(dataset["rooms"]),
        "campuses": len(dataset["campuses"]),
        "scheduled_sessions": metrics["scheduled_sessions"],
        "expected_sessions": metrics["expected_sessions"],
        "session_completion": metrics["session_completion"]
    }

    return render_template(
        "settings.html",
        system_info=system_info
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=True,
        port=5001
    )