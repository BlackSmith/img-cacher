import datetime
import hashlib
import json

from loggate import get_logger
from redis.commands.search.query import Query
from redis.exceptions import LockError

from libs.redis_manager import RedisManager
from libs.socket_manager import socket_command

logger = get_logger('ImageTask')


class ImageTask:
    STATUS_READY = 'ready'
    STATUS_RUNNING = 'running'
    STATUS_ERROR = 'error'
    STATUS_DONE = 'done'

    task_lock = None

    @classmethod
    def get_lock(cls):
        if not cls.task_lock:
            cls.task_lock = RedisManager.get_lock('task_lock_key', timeout=20)
        return cls.task_lock

    @socket_command('add_task')
    @classmethod
    async def ws_add_task(cls, payload, db, **kwargs):
        params = payload.get('params')
        task = ImageTask(**params)
        async with cls.get_lock():
            await task.save(db)

    @classmethod
    async def take_ready_task(cls, db: RedisManager,
                              task_uuid=None) -> 'ImageTask':
        try:
            async with cls.get_lock():
                if task_uuid is None:
                    query = Query(f'@status:{cls.STATUS_READY}').dialect(2)
                    result = await db.ix_tasks.search(query)
                    if result.total == 0:
                        return None
                    task_data = result.docs[0].__dict__
                    task_data.pop('payload')
                    _, task_uuid = task_data.pop('id').split(':', 1)
                else:
                    task_data = await db.r.hgetall(task_uuid)
                if task_data.get('status') != cls.STATUS_READY:
                    return
                if 'action' not in task_data:
                    return
                task_data['action'] = json.loads(task_data['action'])
                task_data['task_uuid'] = task_uuid.replace('tasks:', '')
                task = ImageTask(**task_data)
                task.run_at = int(datetime.datetime.now().timestamp())
                await db.r.hset(task_uuid, 'status', cls.STATUS_RUNNING)
                return task
        except LockError:
            logger.error('I can not get the task lock.')
        return

    def __init__(self, **kwargs):
        if not kwargs.get('status'):
            kwargs['status'] = self.STATUS_READY
        self.action = {}
        self.task_uuid = None
        self.status = None
        self.__dict__.update(kwargs)

    @property
    def data(self):
        return {key: val for key, val in self.__dict__.items() if
                val and not key.startswith('_')}

    def set_action(self, **kwargs):
        self.action.update(kwargs)
        return self

    async def set_error(self, db: RedisManager, msg=None):
        async with self.get_lock():
            await db.r.hset(f'tasks:{self.task_uuid}', 'status',
                            self.STATUS_ERROR)
            if msg:
                logger.error(msg)
                await db.r.hset(f'tasks:{self.task_uuid}',
                                'error_message', msg)

    async def set_done(self, db: RedisManager, msg: str = None):
        async with self.get_lock():
            await db.r.hset(f'tasks:{self.task_uuid}', 'status',
                            self.STATUS_DONE)
            if msg:
                logger.debug(msg)
                await db.r.hset(f'tasks:{self.task_uuid}', 'message', msg)

    async def save(self, db: RedisManager):
        data = self.data
        data['action'] = json.dumps(data['action'])
        if not self.task_uuid:
            self.task_uuid = str(hashlib.md5(
                repr(sorted(self.data.items())).encode()).hexdigest())
        async with self.get_lock():
            await db.r.hset(f'tasks:{self.task_uuid}', mapping=data)
            await db.r.expire(f'tasks:{self.task_uuid}', 1800)
