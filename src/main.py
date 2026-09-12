from pathlib import Path
import pandas as pd
import json

from data_loader import load_dataset, get_schedule_config
from models import build_class_data
from conflict_graph import build_conflict_graph
from graph_coloring import welsh_powell
from greedy_solver import schedule_quarter
from backtracking import repair_schedule
from dp_optimizer import optimize_rooms
from validator import validate_dataset, validate_schedule


def prepare_rooms(data):
    buildings = data["buildings"].set_index("building_id")["campus_id"].to_dict()
    rooms = data["rooms"].to_dict("records")

    for room in rooms:
        room["campus_id"] = buildings[room["building_id"]]

    return rooms


def load_professor_preferences():
    preferences_file = Path(__file__).parent.parent / "data" / "professor_preferences.json"

    if not preferences_file.exists():
        return {}

    try:
        with open(preferences_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def run():
    data = load_dataset()

    print("\nSI UNIVERSITY SCHEDULER")
    print("=" * 55)

    print("\nDATASET")
    print("-" * 55)
    print("Classes:", len(data["classes"]))
    print("Students:", len(data["students"]))
    print("Professors:", len(data["professors"]))
    print("Rooms:", len(data["rooms"]))
    print("Campuses:", len(data["campuses"]))

    if not validate_dataset(data):
        print("Dataset validation failed.")
        return

    print("Dataset: VALID")

    schedule_config = get_schedule_config(data)

    print("Teaching days:", ", ".join(schedule_config["teaching_days"]))
    print("Teaching window:", schedule_config["teaching_start"], "-", schedule_config["teaching_end"])
    print("Scheduling interval:", schedule_config["scheduling_interval_minutes"], "minutes")

    professor_preferences = load_professor_preferences()
    print("Professor preferences loaded:", len(professor_preferences))

    classes = build_class_data(data)
    rooms = prepare_rooms(data)

    all_schedule = []
    all_failed = []
    algorithm_results = []

    for quarter in sorted(set(item["quarter_id"] for item in classes)):
        quarter_classes = [
            item for item in classes
            if item["quarter_id"] == quarter
        ]

        print(f"\n{quarter}")
        print("-" * 40)

        graph = build_conflict_graph(quarter_classes)
        colors = welsh_powell(graph)

        print("Graph colors:", len(set(colors.values())))

        greedy_schedule, failed = schedule_quarter(
            quarter_classes,
            rooms,
            colors,
            schedule_config,
            professor_preferences
        )

        print("Greedy sessions:", len(greedy_schedule))
        print("Greedy failed classes:", len(failed))

        greedy_waste = sum(
            item["capacity"] - item["student_count"]
            for item in greedy_schedule
        )

        print("Greedy room waste:", greedy_waste)

        final_schedule = greedy_schedule
        repaired = 0

        if failed:
            final_schedule, remaining = repair_schedule(
                greedy_schedule,
                failed,
                schedule_config,
                professor_preferences
            )

            repaired = len(failed) - len(remaining)

        print("Backtracking repaired:", repaired)

        final_schedule, unassigned, dp_waste = optimize_rooms(
            final_schedule,
            rooms,
            schedule_config
        )

        print("Rooms assigned:", len(final_schedule))
        print("Unassigned sessions:", len(unassigned))
        print("DP room waste:", dp_waste)

        improvement = greedy_waste - dp_waste

        algorithm_results.append({
            "quarter": quarter,
            "greedy": greedy_waste,
            "dp": dp_waste,
            "improvement": improvement
        })

        print("Room waste improvement:", improvement)

        if improvement > 0:
            print("DP improved the Greedy solution.")
        elif improvement == 0:
            print("DP found the same room waste as Greedy.")
        else:
            print("Greedy had lower room waste.")

        if final_schedule:
            campus_matches = sum(
                item["campus_id"] == item["room_campus_id"]
                for item in final_schedule
            )

            campus_rate = campus_matches / len(final_schedule) * 100

            print("Preferred campus matches:", campus_matches, "/", len(final_schedule))
            print("Campus match rate:", round(campus_rate, 2), "%")

            total_students = sum(item["student_count"] for item in final_schedule)
            total_capacity = sum(item["capacity"] for item in final_schedule)
            utilization = total_students / total_capacity * 100

            print("Room utilization:", round(utilization, 2), "%")

        report = validate_schedule(final_schedule, quarter_classes)

        print("Professor conflicts:", report["professor_conflicts"])
        print("Group conflicts:", report["group_conflicts"])
        print("Room conflicts:", report["room_conflicts"])
        print("Capacity errors:", report["capacity_errors"])
        print("Session errors:", report["session_errors"])

        if report["valid"] and not unassigned and report["session_errors"] == 0:
            print("Final status: VALID")
        else:
            print("Final status: BEST EFFORT")

        scheduled_ids = {item["class_id"] for item in final_schedule}

        failed_ids = [
            item["class_id"]
            for item in quarter_classes
            if item["class_id"] not in scheduled_ids
        ]

        all_failed.extend(failed_ids)

        print("\nSAMPLE SCHEDULE")
        print("-" * 40)

        for item in final_schedule[:10]:
            print(
                item["class_id"],
                "|",
                item["module_name"],
                "|",
                item["day"],
                item["start_time"],
                "|",
                item["room_id"],
                "|",
                item["capacity"],
                "seats",
                "| Campus:",
                item["room_campus_id"]
            )

        all_schedule.extend(final_schedule)

    output = Path(__file__).parent.parent / "output"
    output.mkdir(exist_ok=True)

    with open(output / "algorithm_results.json", "w", encoding="utf-8") as file:
        json.dump(algorithm_results, file, indent=4)

    if all_schedule:
        columns = [
            "quarter_id",
            "class_id",
            "module_name",
            "programme_name",
            "campus_id",
            "professor_id",
            "group_ids",
            "student_count",
            "day",
            "start_time",
            "duration_hours",
            "room_id",
            "capacity",
            "room_campus_id"
        ]

        df = pd.DataFrame(all_schedule)
        columns = [column for column in columns if column in df.columns]
        df[columns].to_csv(output / "final_schedule.csv", index=False)

    if all_failed:
        pd.DataFrame({
            "class_id": sorted(set(all_failed))
        }).to_csv(output / "conflict_report.csv", index=False)

    print("\nOVERALL SUMMARY")
    print("-" * 55)

    print("Total expected sessions:", sum(item["sessions_per_week"] for item in classes))
    print("Total scheduled sessions:", len(all_schedule))
    print("Total failed classes:", len(set(all_failed)))

    if all_schedule:
        total_students = sum(item["student_count"] for item in all_schedule)
        total_capacity = sum(item["capacity"] for item in all_schedule)
        overall_utilization = total_students / total_capacity * 100

        print("Overall room utilization:", round(overall_utilization, 2), "%")

        campus_matches = sum(
            item["campus_id"] == item["room_campus_id"]
            for item in all_schedule
        )

        campus_rate = campus_matches / len(all_schedule) * 100
        print("Overall campus match rate:", round(campus_rate, 2), "%")

    print("\nSCHEDULER COMPLETE")
    print("=" * 55)
    print("Final schedule:", "output/final_schedule.csv")

    if all_failed:
        print("Conflict report:", "output/conflict_report.csv")


if __name__ == "__main__":
    run()