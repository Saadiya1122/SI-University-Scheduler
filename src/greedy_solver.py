from data_loader import load_dataset, get_schedule_config
from models import build_class_data


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIMES = [
    "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "12:30",
    "13:00", "13:30", "14:00", "14:30",
    "15:00"
]


def time_to_minutes(time):
    hour, minute = map(int, time.split(":"))
    return hour * 60 + minute


def minutes_to_time(minutes):
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def generate_times(teaching_start, teaching_end, interval_minutes):
    start = time_to_minutes(teaching_start)
    end = time_to_minutes(teaching_end)

    if interval_minutes <= 0:
        raise ValueError("scheduling_interval_minutes must be greater than 0.")

    times = []
    current = start

    while current < end:
        times.append(minutes_to_time(current))
        current += interval_minutes

    return times


def get_blocks(
    start,
    duration,
    interval_minutes=30,
    teaching_end_minutes=17 * 60
):
    start_minutes = time_to_minutes(start)
    duration_minutes = int(round(duration * 60))

    if interval_minutes <= 0:
        return []

    if duration_minutes % interval_minutes != 0:
        return []

    block_count = duration_minutes // interval_minutes
    blocks = []

    for i in range(block_count):
        total = start_minutes + i * interval_minutes

        if total >= teaching_end_minutes:
            return []

        blocks.append(minutes_to_time(total))

    return blocks


def overlaps(a, b):
    return bool(set(a) & set(b))


def can_schedule(
    class_item,
    day,
    start,
    room,
    schedule,
    teaching_end="17:00",
    interval_minutes=30,
    professor_preferences=None
):
    teaching_end_minutes = time_to_minutes(teaching_end)

    if professor_preferences:
        professor_id = str(class_item["professor_id"]).strip()
        preference = professor_preferences.get(professor_id)

        if preference:
            availability = preference.get("availability", {})
            day_settings = availability.get(day)

            if day_settings:
                if day_settings.get("status", "available") == "unavailable":
                    return False

                available_start = day_settings.get(
                    "start_time",
                    "09:00"
                )
                available_end = day_settings.get(
                    "end_time",
                    teaching_end
                )

                if time_to_minutes(start) < time_to_minutes(available_start):
                    return False

                session_end = (
                    time_to_minutes(start)
                    + class_item["duration_hours"] * 60
                )

                if session_end > time_to_minutes(available_end):
                    return False

    blocks = get_blocks(
        start,
        class_item["duration_hours"],
        interval_minutes,
        teaching_end_minutes
    )

    if not blocks:
        return False

    end = (
        time_to_minutes(start)
        + class_item["duration_hours"] * 60
    )

    if end > teaching_end_minutes:
        return False

    if room["capacity"] < class_item["student_count"]:
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

        if item["room_id"] == room["room_id"]:
            return False

    return True


def get_day_load(schedule, day):
    load = 0

    for item in schedule:
        if item["day"] == day:
            load += len(item["blocks"])

    return load


def get_time_load(schedule, day, start, duration, interval_minutes=30):
    blocks = get_blocks(
        start,
        duration,
        interval_minutes,
        24 * 60
    )

    load = 0

    for item in schedule:
        if item["day"] != day:
            continue

        if overlaps(blocks, item["blocks"]):
            load += 1

    return load


def schedule_quarter(
    classes,
    rooms,
    colors=None,
    config=None,
    professor_preferences=None,
    first_fit=False
):
    schedule = []
    unscheduled = []

    if colors is None:
        colors = {}

    if config is None:
        config = {
            "teaching_days": DAYS,
            "teaching_start": "09:00",
            "teaching_end": "17:00",
            "scheduling_interval_minutes": 30
        }

    teaching_days = config["teaching_days"]
    teaching_start = config["teaching_start"]
    teaching_end = config["teaching_end"]
    interval_minutes = config["scheduling_interval_minutes"]

    times = generate_times(
        teaching_start,
        teaching_end,
        interval_minutes
    )

    # Stage 1:
    # Sort classes by size, largest first.
    #
    # Stage 2:
    # When Welsh-Powell colors are provided,
    # use the color first and class size second.
    if colors:
        classes = sorted(
            classes,
            key=lambda x: (
                colors.get(x["class_id"], 999),
                -x["student_count"]
            )
        )
    else:
        classes = sorted(
            classes,
            key=lambda x: -x["student_count"]
        )

    for class_item in classes:
        placed = []
        used_days = set()

        for _ in range(class_item["sessions_per_week"]):
            found = False

            # Stage 1 first-fit:
            # check days in their original order.
            if first_fit:
                ordered_days = teaching_days
            else:
                # Graph-guided version keeps the previous
                # load-balancing behaviour.
                ordered_days = sorted(
                    teaching_days,
                    key=lambda day: (
                        day in used_days,
                        get_day_load(schedule, day),
                        teaching_days.index(day)
                    )
                )

            for day in ordered_days:

                # Stage 1 first-fit:
                # check times from earliest to latest.
                if first_fit:
                    ordered_times = times

                # Stage 2:
                # Welsh-Powell color gives this class a preferred time position.
                elif colors and class_item["class_id"] in colors:
                    preferred_index = colors[class_item["class_id"]]

                    ordered_times = sorted(
                        times,
                        key=lambda start: (
                            get_time_load(
                                schedule,
                                day,
                                start,
                                class_item["duration_hours"],
                                interval_minutes
                            ),
                            abs(times.index(start) - preferred_index),
                            times.index(start)
                        )
                    )
                else:
                    ordered_times = sorted(
                        times,
                        key=lambda start: (
                            get_time_load(
                                schedule,
                                day,
                                start,
                                class_item["duration_hours"],
                                interval_minutes
                            ),
                            times.index(start)
                        )
                    )

                for start in ordered_times:

                    # Stage 1 first-fit:
                    # simply test rooms in the original order.
                    if first_fit:
                        candidates = rooms

                    else:
                        # Graph-guided version:
                        # prefer rooms on the same campus and
                        # choose smaller suitable rooms first.
                        same_campus = [
                            room
                            for room in rooms
                            if room.get("campus_id")
                            == class_item["campus_id"]
                        ]

                        other_rooms = [
                            room
                            for room in rooms
                            if room.get("campus_id")
                            != class_item["campus_id"]
                        ]

                        candidates = (
                            sorted(
                                same_campus,
                                key=lambda x: x["capacity"]
                            )
                            + sorted(
                                other_rooms,
                                key=lambda x: x["capacity"]
                            )
                        )

                    for room in candidates:
                        if can_schedule(
                            class_item,
                            day,
                            start,
                            room,
                            schedule + placed,
                            teaching_end,
                            interval_minutes,
                            professor_preferences
                        ):
                            placed.append({
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
                                ),
                                "room_id": room["room_id"],
                                "capacity": room["capacity"],
                                "room_campus_id": room["campus_id"]
                            })

                            used_days.add(day)
                            found = True
                            break

                    if found:
                        break

                if found:
                    break

            if not found:
                break

        if len(placed) == class_item["sessions_per_week"]:
            schedule.extend(placed)
        else:
            unscheduled.append(class_item)

    return schedule, unscheduled


if __name__ == "__main__":
    data = load_dataset()
    config = get_schedule_config(data)
    classes = build_class_data(data)

    buildings = (
        data["buildings"]
        .set_index("building_id")["campus_id"]
        .to_dict()
    )

    rooms = data["rooms"].to_dict("records")

    for room in rooms:
        room["campus_id"] = buildings[room["building_id"]]

    print("\nSI UNIVERSITY GREEDY BASELINE")
    print("-" * 50)
    print(
        "Teaching days:",
        ", ".join(config["teaching_days"])
    )
    print(
        "Teaching window:",
        config["teaching_start"],
        "-",
        config["teaching_end"]
    )
    print(
        "Scheduling interval:",
        config["scheduling_interval_minutes"],
        "minutes"
    )

    for quarter in sorted(
        set(item["quarter_id"] for item in classes)
    ):
        quarter_classes = [
            item
            for item in classes
            if item["quarter_id"] == quarter
        ]

        schedule, unscheduled = schedule_quarter(
            quarter_classes,
            rooms,
            config=config,
            first_fit=True
        )

        waste = sum(
            item["capacity"] - item["student_count"]
            for item in schedule
        )

        print(
            quarter,
            "->",
            len(schedule),
            "sessions |",
            len(unscheduled),
            "failed classes | waste:",
            waste
        )