import abc

from loggate import get_logger

logger = get_logger('plugin')


class Plugin:
    EVENTS = {}
    EVENT_PARSE_URL = 1
    EVENT_OPEN_IMAGE = 2

    @classmethod
    def __init_subclass__(cls, **kwargs):
        if not kwargs.get('skip'):
            callbacks = cls.get_callbacks()
            for key, val in callbacks.items():
                if key not in cls.EVENTS:
                    cls.EVENTS[key] = []
                if not isinstance(val, list):
                    val = [val]
                cls.EVENTS[key].extend(val)

    @classmethod
    @abc.abstractmethod
    def get_callbacks(cls) -> {}:
        pass

    @classmethod
    async def run(cls, key, params: dict):
        for call in cls.EVENTS.get(key, []):
            try:
                await call(key, params)
            except Exception as ex:
                logger.warning(f"The callback {key}:{call} failed.",
                               exc_info=ex)
