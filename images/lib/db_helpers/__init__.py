def deserialize_db_item(item) -> dict:
    """Deserializes an item from dynamodb and returns the item as a Dict

    Args:
        item (Dict): Dict containing serialized values.

    Returns:
        dict: Deserialized dynamodb item
    """
    new_item = {}
    for key in item:
        new_item[key] = extract_value(item[key])

    return new_item


def extract_value(dictionary):
    """Helper method which extracts value based on data type of the dynamodb attribute.

    Args:
        dictionary (Dict): Containing the serialized attribute from dynamodb

    Returns:
        Any: If attribute is String, will return String. Likewise for arrays, maps, numbers etc.
    """
    data_type, value = list(dictionary.keys())[0], list(dictionary.values())[0]

    if data_type == "S":
        return value
