import loggate


def dict_bytes2str(dd):
    res = {}
    for k in dd.keys():
        key = k.decode() if isinstance(k, bytes) else k
        if isinstance(dd[k], bytes):
            res[key] = dd[k].decode()
        else:
            res[key] = dd[k]
    return res


def login_required(fce):
    async def run(*args, **kwargs):
        if getattr(kwargs.get('socket', {}), 'user_data', None) is None:
            loggate.get_logger('user').error('Access forbidden.')
            return {'status': 'ng', 'msg': 'Access forbidden.'}
        return await fce(*args, **kwargs)

    return run
