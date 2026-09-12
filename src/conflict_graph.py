from collections import defaultdict
from data_loader import load_dataset
from models import build_class_data


def build_conflict_graph(classes):
    graph = {item["class_id"]: set() for item in classes}

    group_classes = defaultdict(list)
    professor_classes = defaultdict(list)

    for item in classes:
        for group_id in item["group_ids"]:
            group_classes[group_id].append(item["class_id"])

        professor_classes[item["professor_id"]].append(item["class_id"])

    for class_list in group_classes.values():
        for i in range(len(class_list)):
            for j in range(i + 1, len(class_list)):
                a = class_list[i]
                b = class_list[j]

                graph[a].add(b)
                graph[b].add(a)

    for class_list in professor_classes.values():
        for i in range(len(class_list)):
            for j in range(i + 1, len(class_list)):
                a = class_list[i]
                b = class_list[j]

                graph[a].add(b)
                graph[b].add(a)

    return graph


if __name__ == "__main__":
    data = load_dataset()
    classes = build_class_data(data)
    graph = build_conflict_graph(classes)

    degrees = [len(neighbours) for neighbours in graph.values()]

    print("\nSI UNIVERSITY CONFLICT GRAPH")
    print("-" * 50)
    print("Classes:", len(graph))
    print("Conflict edges:", sum(degrees) // 2)
    print("Average degree:", round(sum(degrees) / len(degrees), 2))
    print("Maximum degree:", max(degrees))

    print("\nTOP 10 MOST CONNECTED CLASSES")
    print("-" * 50)

    top = sorted(graph.items(),key=lambda x: len(x[1]),reverse=True )[:10]

    for class_id, neighbours in top:
        print(class_id, "->", len(neighbours), "conflicts")