import asyncio
from typing import Callable

from loggate import get_logger
from redis import exceptions
from redis.asyncio import Redis
from redis.asyncio.lock import Lock
from redis.commands.search import AsyncSearch
from redis.commands.search.field import TagField, TextField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

from config import get_config


class RedisManagerException(Exception): pass    # noqa


def redis_subscribe(topic: str, app: str = None):
    def wrap(fce):
        if get_config('APP_TYPE') == app:
            RedisManager.register_handlers(topic, fce)
        return fce

    return wrap


class RedisManager:
    instance = None
    handlers = {}

    @classmethod
    def get(cls) -> 'RedisManager':
        return cls.instance

    @classmethod
    def get_lock(cls, name, timeout=None):
        return Lock(cls.instance, name, timeout=timeout)

    @classmethod
    def register_handlers(cls, name: str, fce: Callable):
        if name not in cls.handlers:
            cls.handlers[name] = []
        cls.handlers[name].append(fce)

    def __init__(self, uri: str, app):
        if self.__class__.instance:
            raise RedisManagerException('Multiple instances of RedisManager')
        self.uri = uri
        self.app = app
        self.r = None
        self.pubsub = None
        self.ix_images: AsyncSearch = None
        self.ix_tasks: AsyncSearch = None
        self.logger = get_logger(self.__class__.__name__)
        self.__class__.instance = self

    async def connection(self, decode_responses=True):
        while True:
            self.r = await Redis.from_url(self.uri,
                                          decode_responses=decode_responses)
            try:
                if (await self.r.config_get('notify-keyspace-events')).get(
                        'notify-keyspace-events') != 'AKE':
                    await self.r.config_set('notify-keyspace-events', 'AKE')
                if self.handlers:
                    self.pubsub = self.r.pubsub()
                    for topic in set(self.handlers.keys()):
                        await self.pubsub.psubscribe(topic)
                    asyncio.create_task(self.redis_watcher(),
                                        name="Redis watcher")
                images_schema = (
                    # TextField('url'),
                    TextField('filename', sortable=True),
                    TagField('collection', sortable=True),
                    NumericField('created', sortable=True)
                )
                task_schema = (TagField('status', sortable=True))
                matrix_schema = (TextField('similar_images_uuids'))
                self.ix_images = self.r.ft('ix:images')
                self.ix_tasks = self.r.ft('ix:tasks')
                self.ix_matrix = self.r.ft('ix:matrix')

                try:
                    await self.ix_matrix.create_index(
                        matrix_schema,
                        definition=IndexDefinition(prefix=["matrix:"],
                                                   index_type=IndexType.HASH))
                    await self.ix_tasks.create_index(
                        task_schema,
                        definition=IndexDefinition(prefix=["tasks:"],
                                                   index_type=IndexType.HASH))
                    await self.ix_images.create_index(
                        images_schema,
                        definition=IndexDefinition(prefix=["images:"],
                                                   index_type=IndexType.HASH))
                except Exception:
                    pass
                return None
            except exceptions.BusyLoadingError:
                self.logger.warning('Redis is busy. Waiting ...')
                await asyncio.sleep(5)
            except exceptions.ConnectionError as ex:
                raise RedisManagerException(ex)

    async def disconnect(self):
        if self.pubsub:
            await self.pubsub.close()
        if self.r:
            await self.r.close(close_connection_pool=True)

    async def redis_watcher(self):
        from .socket_manager import SocketManager
        socket = SocketManager.get()
        rename_from = None
        while True:
            if msg := await self.pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=None):
                params = {}
                pattern = msg.get('pattern')
                channel = msg.get('channel')
                action = msg.get('data')
                if action == 'rename_from':
                    rename_from = channel
                    continue
                elif action == 'rename_to':
                    params['rename_from'] = rename_from
                    rename_from = None
                if pattern:
                    for fce in self.handlers.get(pattern, []):
                        try:
                            await fce(channel=channel, action=action, db=self,
                                      socket=socket, **params)
                        except Exception as ex:
                            print(fce)
                            self.logger.error(ex, exc_info=ex)

    def __getattr__(self, item):
        return getattr(self.r, item)
