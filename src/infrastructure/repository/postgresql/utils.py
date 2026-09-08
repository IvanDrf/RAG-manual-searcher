from functools import wraps


def execute_once(func):
    res = None

    @wraps
    async def wrapper(*args, **kwargs):
        nonlocal res
        if res is None:
            res = await func(*args, **kwargs)

        return res

    return wrapper
