


def parse_json(x, return_attr, check_attr="", check_value="", output_type="list", list_length=-1):
    result_list = []
    for dic in x:
        if not check_attr:
            result_list.append(dic[return_attr])
        else:
            if check_value == dic[check_attr]:
                result_list.append(dic[return_attr])
    if output_type == "list":
        if list_length == -1 or len(result_list) < list_length:
            return result_list
        else:
            return result_list[:list_length]
    elif output_type == "str":
        if len(result_list) == 0:
            return ''
        else:
            if len(result_list) > 1:
                print("There are more than one value: check_value={}, list={}".format(check_value, result_list))
            return result_list[0]
