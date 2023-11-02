import os
from collections import OrderedDict

from redis.commands.search.query import Query

from config import get_config
from libs.redis_manager import RedisManager

THUMB_HEIGHT = get_config('THUMB_HEIGHT', wrapper=int)
THUMB_WIDTH = get_config('THUMB_WIDTH', wrapper=int)
DATA_DIR = get_config('DATA_DIR')


class CollectionException(Exception): pass      # noqa


class Collection:

    @staticmethod
    def get_uuid_from_link(link):
        _, uuid, cuuid = link.split(':', 2)
        return f'{uuid}:{cuuid}' if cuuid != '@' else uuid

    @classmethod
    async def get_collections(cls, *, db: RedisManager, **kwargs):
        result = []
        for it in await db.ix_images.tagvals('collection'):
            if it != '@':
                # if data := await db.r.hgetall(f'collections:{it}'):
                # TODO: add private collection
                res = await db.ix_images.search(
                    Query(f'@collection:{{{it}}}').no_content())
                if res.total > 0:
                    result.append({'name': it, 'num_member': res.total})
        return result

    @classmethod
    async def get(cls, name: str, db: RedisManager, offset: int = 0,
                  num: int = 100) -> 'Collection':
        data = await db.r.hgetall(f'collections:{name}:detail')
        # members = sorted(members.values(), key=lambda a: a[0]['created'])
        # members.reverse()
        return Collection(name, data)

    def __init__(self, name: str, data: dict = None):
        self.name = name
        self.thumb_file = None
        if data:
            self.__dict__.update(data)

    @property
    def data(self):
        res = {}
        for key, val in self.__dict__.items():
            if val and \
                    not key.startswith('_') and key not in ['name', 'members']:
                res[key] = val
        return res

    @property
    def full_thumb_image_path(self):
        if self.thumb_file:
            return f'{DATA_DIR}/{self.thumb_file}'

    def __repr__(self):
        return f'Collection(name: {self.name}, {self.data})'

    async def make_thumb(self, db: RedisManager, force=False):
        from modules.image_task import ImageTask
        if not self.full_thumb_image_path or not os.path.exists(
                self.full_thumb_image_path) or force:
            task2 = ImageTask().set_action(
                collection=self.name,
                cmd='make_gif_from_images',
                width=THUMB_WIDTH,
                height=THUMB_HEIGHT,
                thumb=True
            )
            await task2.save(db)

    async def get_members(self, db, offset: int = 0, num: int = 10000,
                          get_alternates: bool = False):
        if num < 0:
            num = 10000
        members = OrderedDict()
        _name = self.name.replace("@", '\\@')
        query = (Query(f'@collection:{{{_name}}}')
                 .sort_by('created', False)
                 .paging(offset, min(num, 10000)))
        for it in (await db.ix_images.search(query)).docs:
            data = it.__dict__
            data.pop('payload')
            data['uuid'] = self.get_uuid_from_link(data.pop('id'))
            rr = data['uuid'].split(':')
            main = rr.pop(0)
            if len(rr) == 0:
                data['alternates_count'] = len(members.get(main, [])) + 1
            if main not in members:
                members[main] = [data]
            else:
                if not rr:
                    # This is main picture
                    members[main].insert(0, data)
                else:
                    # Alternates
                    if 'alternates_count' in members[main][0]:
                        members[main][0]['alternates_count'] += 1
                    members[main].append(data)
        if get_alternates:
            return list(members.values())
        else:
            return [it[0] for it in members.values()]

    async def save(self, db: RedisManager, pipe=None):
        if not pipe:
            pipe = db.r
        if self.data:
            await pipe.hset(f'collections:{self.name}:detail',
                            mapping=self.data)

    async def delete(self, db: RedisManager, pipe=None):
        # if self.members:
        #     raise CollectionException('Can not delete non-empty collection')
        if not pipe:
            pipe = db.r
        await pipe.delete(f'collections:{self.name}:detail')
