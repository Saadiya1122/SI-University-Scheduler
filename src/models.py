from collections import defaultdict
from data_loader import load_dataset


def build_class_data(data):
    classes = data["classes"]
    class_groups = data["class_groups"]
    groups = data["student_groups"]
    quarter_modules = data["quarter_modules"]
    modules = data["modules"]
    programmes = data["programmes"]

    group_lookup = groups.set_index("group_id").to_dict("index")
    module_lookup = modules.set_index("module_id").to_dict("index")
    programme_lookup = programmes.set_index("programme_id").to_dict("index")
    qm_lookup = quarter_modules.set_index("quarter_module_id").to_dict("index")

    class_group_lookup = defaultdict(list)

    for _, row in class_groups.iterrows():
        class_group_lookup[row["class_id"]].append(row["group_id"])

    result = []

    for _, row in classes.iterrows():
        qm = qm_lookup[row["quarter_module_id"]]
        module = module_lookup[qm["module_id"]]
        programme = programme_lookup[qm["programme_id"]]
        group_ids = class_group_lookup[row["class_id"]]

        student_count = sum(
            group_lookup[group_id]["student_count"]
            for group_id in group_ids
        )

        result.append({
            "class_id": row["class_id"],
            "module_id": qm["module_id"],
            "module_code": module["module_code"],
            "module_name": module["module_name"],
            "professor_id": row["professor_id"],
            "group_ids": group_ids,
            "student_count": student_count,
            "sessions_per_week": int(row["sessions_per_week"]),
            "duration_hours": float(row["duration_hours"]),
            "programme_id": qm["programme_id"],
            "programme_name": programme["programme_name"],
            "campus_id": programme["primary_campus_id"],
            "year_of_study": int(qm["year_of_study"]),
            "quarter_id": qm["quarter_id"]
        })

    return result


if __name__ == "__main__":
    data = load_dataset()
    class_data = build_class_data(data)

    print("\nCLASS DATA")
    print("-" * 50)

    for item in class_data[:5]:
        print(item)

    group_counts = [len(item["group_ids"]) for item in class_data]
    student_counts = [item["student_count"] for item in class_data]

    print("\nCLASS GROUP PROFILE")
    print("-" * 50)
    print("Total classes:", len(class_data))
    print("Average groups per class:", round(sum(group_counts) / len(group_counts), 2))
    print("Maximum groups:", max(group_counts))
    print("Classes with multiple groups:", sum(x > 1 for x in group_counts))
    print("Average students:", round(sum(student_counts) / len(student_counts), 2))
    print("Largest class:", max(student_counts))
    print("Smallest class:", min(student_counts))