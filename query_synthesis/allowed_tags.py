import json


def get_allowed_tags_recursive(tags_tree):
    allowed_tags = []
    for key, value in tags_tree.items():
        allowed_tags.append(key)
        if value:
            allowed_tags.extend(get_allowed_tags_recursive(value))
    return allowed_tags

def get_allowed_tags():
    with open('./dataset/cata_tree.json', 'r', encoding='utf-8') as f:
        tags_tree = json.load(f)
    allowed_tags = get_allowed_tags_recursive(tags_tree)
    return allowed_tags


if __name__ == "__main__":
    allowed_tags = get_allowed_tags()
    print(allowed_tags)
    print(len(allowed_tags))

