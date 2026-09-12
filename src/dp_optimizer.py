from functools import lru_cache


def get_minutes(time):
    hour, minute = map(int, time.split(":"))
    return hour * 60 + minute


def room_dp(sessions, rooms):
    if not sessions or len(sessions) > len(rooms):
        return None

    order = sorted(range(len(sessions)),key=lambda i: sessions[i]["student_count"])

    room_order = sorted(range(len(rooms)),key=lambda i: rooms[i]["capacity"])

    n = len(order)
    m = len(room_order)

    @lru_cache(None)
    def dp(i, j):
        if i == n:
            return 0

        if m - j < n - i:
            return float("inf")

        best = dp(i, j + 1)

        room = rooms[room_order[j]]
        student_count = sessions[order[i]]["student_count"]

        if room["capacity"] >= student_count:
            waste = room["capacity"] - student_count
            use = waste + dp(i + 1, j + 1)
            best = min(best, use)

        return best

    minimum_waste = dp(0, 0)

    if minimum_waste == float("inf"):
        return None

    assignment = [None] * len(sessions)
    i = 0
    j = 0

    while i < n:
        if j == m:
            return None

        skip = dp(i, j + 1)

        room = rooms[room_order[j]]
        student_count = sessions[order[i]]["student_count"]
        use = float("inf")

        if room["capacity"] >= student_count:
            waste = room["capacity"] - student_count
            use = waste + dp(i + 1, j + 1)

        if use <= skip:
            assignment[order[i]] = room
            i += 1
            j += 1
        else:
            j += 1

    if any(room is None for room in assignment):
        return None

    return assignment


def better_campus_assignment(sessions, assignment):
    improved = True

    while improved:
        improved = False

        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                room_a = assignment[i]
                room_b = assignment[j]

                current_matches = 0

                if room_a["campus_id"] == sessions[i]["campus_id"]:
                    current_matches += 1

                if room_b["campus_id"] == sessions[j]["campus_id"]:
                    current_matches += 1

                new_match_a = 0
                new_match_b = 0

                if room_b["campus_id"] == sessions[i]["campus_id"]:
                    new_match_a = 1

                if room_a["campus_id"] == sessions[j]["campus_id"]:
                    new_match_b = 1

                new_matches = new_match_a + new_match_b

                if new_matches <= current_matches:
                    continue

                if room_b["capacity"] < sessions[i]["student_count"]:
                    continue

                if room_a["capacity"] < sessions[j]["student_count"]:
                    continue

                current_waste = (room_a["capacity"] - sessions[i]["student_count"]+ room_b["capacity"] - sessions[j]["student_count"])

                new_waste = (room_b["capacity"] - sessions[i]["student_count"]+ room_a["capacity"] - sessions[j]["student_count"])

                if new_waste <= current_waste:
                    assignment[i] = room_b
                    assignment[j] = room_a
                    improved = True

    return assignment


def calculate_waste(schedule):
    return sum(item["capacity"] - item["student_count"] for item in schedule)


def optimize_rooms(schedule, rooms, config=None):
    original_schedule = [dict(item) for item in schedule]
    original_waste = calculate_waste(original_schedule)
    result = [dict(item) for item in schedule]

    original_rooms = {}

    for item in result:
        key = (item["class_id"],item["day"],item["start_time"])

        original_rooms[key] = {
            "room_id": item.get("room_id"),
            "capacity": item.get("capacity"),
            "campus_id": item.get(
                "room_campus_id",
                item.get("campus_id")
            )
        }

        item.pop("room_id", None)
        item.pop("capacity", None)
        item.pop("room_campus_id", None)

        start_minutes = get_minutes(item["start_time"])
        item["_end"] = start_minutes + item["duration_hours"] * 60

    if config is None:
        config = {
            "teaching_days": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday"
            ],
            "teaching_start": "09:00",
            "teaching_end": "17:00",
            "scheduling_interval_minutes": 30
        }

    days = config["teaching_days"]

    day_order = {day: i for i, day in enumerate(days)}

    starts = sorted(
        set((item["day"], item["start_time"]) for item in result),
        key=lambda x: (day_order.get(x[0], len(day_order)),get_minutes(x[1])))

    active = []

    for day, start in starts:
        start_minutes = get_minutes(start)

        active = [item for item in active if item["_end"] > start_minutes]

        current = [
            item
            for item in result
            if item["day"] == day and item["start_time"] == start]

        used_rooms = {item["room_id"]
            for item in active
            if item.get("room_id") is not None}

        available = [room for room in rooms if room["room_id"] not in used_rooms]

        assignment = room_dp(current, available)

        if assignment is not None:
            assignment = better_campus_assignment(
                current,
                assignment)

            for session, room in zip(current, assignment):
                session["room_id"] = room["room_id"]
                session["capacity"] = room["capacity"]
                session["room_campus_id"] = room["campus_id"]
        else:
            for session in current:
                key = (session["class_id"], session["day"],session["start_time"])

                old = original_rooms[key]

                session["room_id"] = old["room_id"]
                session["capacity"] = old["capacity"]
                session["room_campus_id"] = old["campus_id"]

        slot_dp_waste = sum(item["capacity"] - item["student_count"] for item in current)

        slot_greedy_waste = sum(
            original_rooms[
                (
                    item["class_id"],
                    item["day"],
                    item["start_time"]
                )
            ]["capacity"] - item["student_count"]
            for item in current
        )

        greedy_rooms_available = all(
            original_rooms[(item["class_id"],item["day"],item["start_time"])]["room_id"] not in used_rooms for item in current)

        if slot_greedy_waste < slot_dp_waste and greedy_rooms_available:
            for session in current:
                key = (session["class_id"],session["day"],session["start_time"])

                old = original_rooms[key]

                session["room_id"] = old["room_id"]
                session["capacity"] = old["capacity"]
                session["room_campus_id"] = old["campus_id"]

        active.extend(current)

    for item in result:
        item.pop("_end", None)

    for i in range(len(result)):
        for j in range(i + 1, len(result)):
            a = result[i]
            b = result[j]

            if a["day"] != b["day"]:
                continue

            a_start = get_minutes(a["start_time"])
            b_start = get_minutes(b["start_time"])

            a_end = a_start + a["duration_hours"] * 60
            b_end = b_start + b["duration_hours"] * 60

            overlap = a_start < b_end and b_start < a_end

            if not overlap:
                continue

            if a["room_id"] == b["room_id"]:
                return original_schedule, [], original_waste

    final_waste = calculate_waste(result)

    if final_waste > original_waste:
        return original_schedule, [], original_waste

    return result, [], final_waste

if __name__ == "__main__":
    print("Dynamic programming room optimizer")