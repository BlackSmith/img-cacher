import re

import yaml


def get_yaml(filename):
    with open(filename, 'r+') as fd:
        return yaml.safe_load(fd)


def update_dict(data: dict, update: dict):
    """
    version: 1.0
    Update dictionary
    E.g.
        data = {'A': 1, 'B': {'BA': 2, 'BB': {'BBA': ['XXX','YYY']}}}
        update = {'B.BB': {'BBA': ['...', 'ZZZ']}}
        update_dict(data, update)
        print(data)
        {'A': 1, 'B': {'BA': 2, 'BB': {'BBA': ['XXX', 'YYY', 'ZZZ']}}}
    """
    for key, val in update.items():
        keys = re.split(r'(?<!\\)\.', key)
        attr = keys.pop().replace('\\', '')
        item = data
        while keys:
            _k = keys.pop(0)
            if _k not in item:
                item[_k] = {}
            item = item[_k]
        if not isinstance(val, dict) or attr not in item:
            if isinstance(val, list) and isinstance(item.get(attr, ''), list) \
                    and '...' in val:
                val.remove('...')
                item[attr] += val
            else:
                item[attr] = val
        else:
            update_dict(item[attr], val)


def dicts_val(path: str, data, **kwargs):
    """
    version: 1.0
    Get value from dictionary tree
    :param path: str (e.g. config.labels.cz\\.alps\\.mantra)
    :param data: dict tree
    :raise KeyError
    :return: Any - return value
    """
    delim = r'(?<!\\)\.' if 'delimiter' not in kwargs else kwargs['delimiter']
    try:
        dd = data
        for it in re.split(delim, path):
            key = it.replace('\\', '')
            if isinstance(dd, list) and key.isnumeric():
                key = int(key)
            dd = dd[key]
        return dd
    except Exception as ex:
        if 'default' in kwargs:
            return kwargs['default']
        raise ex


def normalize_filename(filename: str) -> str:
    filename = filename.lower()
    filename = re.sub(r'\s', '-', filename)
    filename = re.sub(r'-{2,}', '-', filename)
    filename = re.sub(r'[^a-zA-Z0-9-_]', '', filename)

    filename = filename[:255]
    return filename


def flatten_data(data: dict, result=None, parent=None, max_deep=3) -> dict:
    """
    This makes a flatted dictionary from incoming message.
        {'mode': {'debug': False}} -> {'mode_debug': False}
    If the key starts with parents name, the key joining is skipped.
        {'wifi': {'wifi_rssi': 10}} -> {'wifi_rssi': 10}
    If the value is list, the key contains index of value in the list.
        {'plc_in': [1]} -> {'plc_in_0': 1}
    The key 'hbl' is skipped always. This key is never joined.
    :param data: dict
    :param result: internal
    :param parent: internal
    :param max_deep: internal
    :return: dict
    """
    if not result:
        result = {}
    for key, val in data.items():
        if isinstance(val, dict) and max_deep > 0:
            # max_deep is a fuse for infinite loop
            result.update(
                flatten_data(
                    val,
                    result,
                    parent=key,
                    max_deep=max_deep - 1)
            )
        elif isinstance(val, list):
            for ix in range(len(val)):
                result[f"{key}_{ix}"] = val[ix]
        else:
            if parent is None or parent and key.startswith(parent):
                result[key] = val
            else:
                result[f"{parent}_{key}"] = val
    return result
