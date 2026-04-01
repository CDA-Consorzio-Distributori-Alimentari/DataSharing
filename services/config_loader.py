import json
from pathlib import Path


def _load_json_file(file_path):
    path = Path(file_path)
    if not path.exists():
        return {}

    with open(path, "r") as file:
        return json.load(file)


def _merge_lists(base_list, override_list):
    if not all(isinstance(item, dict) and item.get("code") for item in base_list + override_list):
        return override_list

    merged_items = {str(item["code"]).strip(): dict(item) for item in base_list}
    ordered_codes = [str(item["code"]).strip() for item in base_list]

    for override_item in override_list:
        item_code = str(override_item["code"]).strip()
        if item_code in merged_items:
            merged_items[item_code] = merge_config_data(merged_items[item_code], override_item)
        else:
            merged_items[item_code] = dict(override_item)
            ordered_codes.append(item_code)

    return [merged_items[item_code] for item_code in ordered_codes]


def merge_config_data(base_data, override_data):
    if isinstance(base_data, dict) and isinstance(override_data, dict):
        merged = dict(base_data)
        for key, value in override_data.items():
            if key in merged:
                merged[key] = merge_config_data(merged[key], value)
            else:
                merged[key] = value
        return merged

    if isinstance(base_data, list) and isinstance(override_data, list):
        return _merge_lists(base_data, override_data)

    return override_data


def load_merged_config(config_file="config.json", local_config_file="config.local.json"):
    config_data = _load_json_file(config_file)
    local_config_data = _load_json_file(local_config_file)
    return merge_config_data(config_data, local_config_data)
