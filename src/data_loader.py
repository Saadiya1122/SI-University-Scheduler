import pandas as pd
from pathlib import Path


DATA_FILE = (Path(__file__).parent.parent / "data"/ "SI_University_Scheduling_Dataset_AUDITED_FINAL.xlsx")


def load_dataset(file_path=DATA_FILE):
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    excel = pd.ExcelFile(file_path)
    data = {}

    for sheet in excel.sheet_names:
        data[sheet] = pd.read_excel(excel, sheet_name=sheet)

    return data


def print_summary(data):
    print("\nSI UNIVERSITY DATASET")
    print("-" * 40)

    for sheet, df in data.items():
        print(f"{sheet}: {len(df)} rows")


def get_schedule_config(data):
    if "university" not in data or data["university"].empty:
        raise ValueError(
            "The dataset must contain a non-empty 'university' sheet.")

    university = data["university"].iloc[0]

    raw_days = str(university.get("teaching_days", "Monday-Friday")).strip()

    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    if "-" in raw_days:
        parts = [part.strip() for part in raw_days.split("-", 1)]

        start_index = weekday_names.index(parts[0])
        end_index = weekday_names.index(parts[1])

        if start_index <= end_index:
            teaching_days = weekday_names[start_index:end_index + 1]
        else:
            teaching_days = (weekday_names[start_index:]+ weekday_names[:end_index + 1])

    elif "," in raw_days:
        teaching_days = [
            day.strip()
            for day in raw_days.split(",")
            if day.strip()
        ]
    else:
        teaching_days = [raw_days]

    interval_value = university.get("scheduling_interval_minutes",30)

    if pd.isna(interval_value):
        interval_value = 30

    return {
        "teaching_days": teaching_days,
        "teaching_start": str(
            university.get("teaching_start", "09:00")
        ).strip(),
        "teaching_end": str(
            university.get("teaching_end", "17:00")
        ).strip(),
        "scheduling_interval_minutes": int(interval_value)
    }


if __name__ == "__main__":
    data = load_dataset()
    print_summary(data)