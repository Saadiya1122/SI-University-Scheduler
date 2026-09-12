from data_loader import load_dataset
from models import build_class_data
from conflict_graph import build_conflict_graph


def welsh_powell(graph):
    degrees = {class_id: len(neighbours) for class_id, neighbours in graph.items()}
    order = sorted(graph, key=lambda x: degrees[x], reverse=True)

    colors = {}
    color = 0

    for class_id in order:
        if class_id in colors:
            continue

        colors[class_id] = color

        for other in order:
            if other in colors:
                continue

            valid = True

            for assigned, color_value in colors.items():
                if color_value == color and assigned in graph[other]:
                    valid = False
                    break

            if valid:
                colors[other] = color

        color += 1

    return colors


def validate_coloring(graph, colors):
    conflicts = 0

    for class_id, neighbours in graph.items():
        for neighbour in neighbours:
            if colors[class_id] == colors[neighbour]:
                conflicts += 1

    return conflicts // 2


if __name__ == "__main__":
    data = load_dataset()
    classes = build_class_data(data)

    print("\nSI UNIVERSITY WELSH-POWELL")
    print("-" * 50)

    for quarter in sorted(set(item["quarter_id"] for item in classes)):
        quarter_classes = [item for item in classes if item["quarter_id"] == quarter]

        graph = build_conflict_graph(quarter_classes)
        colors = welsh_powell(graph)
        conflicts = validate_coloring(graph, colors)

        print(f"\n{quarter}")
        print("-" * 30)
        print("Classes:", len(graph))
        print("Colors used:", len(set(colors.values())))
        print("Coloring conflicts:", conflicts)

        if conflicts == 0:
            print("Status: VALID")
        else:
            print("Status: INVALID")