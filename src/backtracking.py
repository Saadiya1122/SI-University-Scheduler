from greedy_solver import get_blocks, overlaps, generate_times, time_to_minutes


def can_place(class_item, day, start, schedule, teaching_end, interval_minutes, professor_preferences=None):
    blocks = get_blocks(start,class_item["duration_hours"],interval_minutes,time_to_minutes(teaching_end))

    if not blocks:
        return False

    if professor_preferences:
        professor_id = str(class_item["professor_id"]).strip()
        preference = professor_preferences.get(professor_id)

        if preference:
            availability = preference.get("availability", {})
            day_settings = availability.get(day)

            if day_settings:
                if day_settings.get("status", "available") == "unavailable":
                    return False

                available_start = day_settings.get("start_time", "09:00")
                available_end = day_settings.get("end_time", teaching_end)

                if time_to_minutes(start) < time_to_minutes(available_start):
                    return False

                session_end = time_to_minutes(start) + class_item["duration_hours"] * 60

                if session_end > time_to_minutes(available_end):
                    return False

    for item in schedule:
        if item["day"] != day:
            continue

        if not overlaps(blocks, item["blocks"]):
            continue

        if item["professor_id"] == class_item["professor_id"]:
            return False

        if set(item["group_ids"]) & set(class_item["group_ids"]):
            return False

        if item["class_id"] == class_item["class_id"]:
            return False

    return True


def make_session(class_item, day, start, interval_minutes, teaching_end):
    return {
        "class_id": class_item["class_id"],
        "module_name": class_item["module_name"],
        "professor_id": class_item["professor_id"],
        "group_ids": class_item["group_ids"],
        "student_count": class_item["student_count"],
        "programme_id": class_item["programme_id"],
        "programme_name": class_item["programme_name"],
        "campus_id": class_item["campus_id"],
        "quarter_id": class_item["quarter_id"],
        "day": day,
        "start_time": start,
        "duration_hours": class_item["duration_hours"],
        "blocks": get_blocks(
            start,
            class_item["duration_hours"],
            interval_minutes,
            time_to_minutes(teaching_end)
        )
    }


def search(tasks, index, schedule, teaching_days, times, interval_minutes, teaching_end, professor_preferences=None):
    if index == len(tasks):
        return True

    class_item = tasks[index]

    for day in teaching_days:
        for start in times:
            if can_place(
                class_item,
                day,
                start,
                schedule,
                teaching_end,
                interval_minutes,
                professor_preferences):
                schedule.append(
                    make_session(
                        class_item,
                        day,
                        start,
                        interval_minutes,
                        teaching_end
                    )
                )

                if search(
                    tasks,
                    index + 1,
                    schedule,
                    teaching_days,
                    times,
                    interval_minutes,
                    teaching_end,
                    professor_preferences):
                    return True

                schedule.pop()

    return False


def repair_schedule(schedule, failed, config=None, professor_preferences=None):
    if config is None:
        config = {
            "teaching_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "teaching_start": "09:00",
            "teaching_end": "17:00",
            "scheduling_interval_minutes": 30}

    teaching_days = config["teaching_days"]
    teaching_start = config["teaching_start"]
    teaching_end = config["teaching_end"]
    interval_minutes = config["scheduling_interval_minutes"]

    times = generate_times(teaching_start, teaching_end, interval_minutes)

    tasks = []

    for item in failed:
        for _ in range(item["sessions_per_week"]):
            tasks.append(item)

    tasks.sort(key=lambda x: x["student_count"], reverse=True)

    repaired = [dict(item) for item in schedule]

    success = search(
        tasks,
        0,
        repaired,
        teaching_days,
        times,
        interval_minutes,
        teaching_end,
        professor_preferences)

    if success:
        return repaired, []

    return schedule, failed


if __name__ == "__main__":
    print("Backtracking is used by main.py to repair failed classes.")