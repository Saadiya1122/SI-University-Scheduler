from data_loader import load_dataset, get_schedule_config


def check_columns(data, table, columns):
    return all(column in data[table].columns for column in columns)


def check_duplicates(data, table, key):
    return not data[table].duplicated(key).any()


def check_missing(data, table, columns):
    return not data[table][columns].isnull().any().any()


def check_reference(data, table, column, target_table, target_column):
    values = set(data[table][column].dropna())
    target = set(data[target_table][target_column].dropna())
    return values <= target


def validate_dataset(data):
    required = {
        "students": ["student_id", "group_id"],
        "student_groups": ["group_id", "programme_id", "year_of_study", "student_count"],
        "classes": ["class_id", "quarter_module_id", "professor_id", "sessions_per_week", "duration_hours"],
        "class_groups": ["class_id", "group_id"],
        "professors": ["professor_id", "faculty_id", "primary_campus_id"],
        "rooms": ["room_id", "building_id", "capacity"],
        "buildings": ["building_id", "campus_id"],
        "campuses": ["campus_id"],
        "modules": ["module_id", "faculty_id"],
        "quarter_modules": ["quarter_module_id", "programme_id", "quarter_id", "module_id"],
        "programmes": ["programme_id", "faculty_id", "primary_campus_id"],
        "academic_calendar": ["quarter_id"]}

    keys = {
        "students": "student_id",
        "student_groups": "group_id",
        "classes": "class_id",
        "professors": "professor_id",
        "rooms": "room_id",
        "buildings": "building_id",
        "campuses": "campus_id",
        "modules": "module_id",
        "quarter_modules": "quarter_module_id",
        "programmes": "programme_id",
        "academic_calendar": "quarter_id"}

    references = [
        ("students", "group_id", "student_groups", "group_id"),
        ("class_groups", "class_id", "classes", "class_id"),
        ("class_groups", "group_id", "student_groups", "group_id"),
        ("classes", "quarter_module_id", "quarter_modules", "quarter_module_id"),
        ("classes", "professor_id", "professors", "professor_id"),
        ("rooms", "building_id", "buildings", "building_id"),
        ("buildings", "campus_id", "campuses", "campus_id"),
        ("professors", "faculty_id", "faculties", "faculty_id"),
        ("professors", "primary_campus_id", "campuses", "campus_id"),
        ("modules", "faculty_id", "faculties", "faculty_id"),
        ("quarter_modules", "programme_id", "programmes", "programme_id"),
        ("quarter_modules", "quarter_id", "academic_calendar", "quarter_id"),
        ("quarter_modules", "module_id", "modules", "module_id"),
        ("programmes", "faculty_id", "faculties", "faculty_id"),
        ("programmes", "primary_campus_id", "campuses", "campus_id")]

    valid = True

    for table, columns in required.items():
        if not check_columns(data, table, columns):
            valid = False

    for table, key in keys.items():
        if not check_duplicates(data, table, key):
            valid = False

    if data["class_groups"].duplicated(["class_id", "group_id"]).any():
        valid = False

    for table, columns in required.items():
        if not check_missing(data, table, columns):
            valid = False

    for reference in references:
        if not check_reference(data, *reference):
            valid = False

    classes = data["classes"]

    try:
        schedule_config = get_schedule_config(data)
        interval_minutes = int(schedule_config["scheduling_interval_minutes"])

        if interval_minutes <= 0:
            valid = False

    except (KeyError, TypeError, ValueError):
        valid = False
        interval_minutes = 30

    sessions_valid = classes["sessions_per_week"].apply(
        lambda value: float(value).is_integer() and int(value) > 0
    ).all()

    if not sessions_valid:
        valid = False

    duration_valid = True

    for value in classes["duration_hours"]:
        try:
            duration_minutes = float(value) * 60

            if duration_minutes <= 0:
                duration_valid = False
                break

            if interval_minutes > 0 and duration_minutes % interval_minutes != 0:
                duration_valid = False
                break

        except (TypeError, ValueError):
            duration_valid = False
            break

    if not duration_valid:
        valid = False

    if (data["rooms"]["capacity"] <= 0).any():
        valid = False

    return valid


def validate_schedule(schedule, classes):
    professor_conflicts = 0
    group_conflicts = 0
    room_conflicts = 0
    capacity_errors = 0
    counts = {}

    for session in schedule:
        class_id = session["class_id"]
        counts[class_id] = counts.get(class_id, 0) + 1

        if "room_id" not in session or "capacity" not in session:
            room_conflicts += 1
            continue

        if session["capacity"] < session["student_count"]:
            capacity_errors += 1

    for i in range(len(schedule)):
        a = schedule[i]

        for j in range(i + 1, len(schedule)):
            b = schedule[j]

            if a["day"] != b["day"]:
                continue

            if not (set(a["blocks"]) & set(b["blocks"])):
                continue

            if a["professor_id"] == b["professor_id"]:
                professor_conflicts += 1

            if set(a["group_ids"]) & set(b["group_ids"]):
                group_conflicts += 1

            if a.get("room_id") and a["room_id"] == b.get("room_id"):
                room_conflicts += 1

    session_errors = 0

    for item in classes:
        expected = item["sessions_per_week"]
        actual = counts.get(item["class_id"], 0)

        if actual != expected:
            session_errors += 1

    valid = (
        professor_conflicts == 0 and group_conflicts == 0 and room_conflicts == 0 and capacity_errors == 0)

    return {
        "valid": valid,
        "professor_conflicts": professor_conflicts,
        "group_conflicts": group_conflicts,
        "room_conflicts": room_conflicts,
        "capacity_errors": capacity_errors,
        "session_errors": session_errors
    }


if __name__ == "__main__":
    data = load_dataset()

    print("\nSI UNIVERSITY DATA VALIDATION")
    print("-" * 50)

    if validate_dataset(data):
        print("DATASET STATUS: VALID")
    else:
        print("DATASET STATUS: INVALID")