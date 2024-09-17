
def std_list(*args):
    if len(args) == 1 and isinstance(args[0], list):
        args = args[0]

    newList = []
    for arg in args:
        if isinstance(arg, list):
            newList.extend(arg)
        else:
            newList.append(arg)

    return newList

def std_index(list, index):
    return list[index]

def std_append(list, item):
    list.append(item)
    return list

def std_extend(list1, list2):
    list1.extend(list2)
    return list1

def std_insert(list, item, index):
    list.insert(index, item)
    return list

def std_remove(list, item):
    list.remove(item)
    return list

def std_pop(list, index=-1):
    return list.pop(index)
