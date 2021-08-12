def get_datatype(variable):
    data_type = type(variable)
    if data_type == str:
        return "S"
    elif data_type == int or data_type == float:
        return "N"
