import asyncio
import datetime
import hashlib
import json
import time
import urllib.parse

import os
import re
from pathlib import Path

import aiohttp
from aiofile import async_open
from loggate import get_logger
from redis.commands.search.query import Query

from config import get_config
from libs.helper import dict_bytes2str
from libs.redis_manager import RedisManager
from modules.collection import Collection
from modules.image_request_parser import ImageRequest
from modules.image_task import ImageTask
from modules.plugins import Plugin

logger = get_logger('image')

DEFAULT_USER_AGENT = get_config('DEFAULT_USER_AGENT')
DOWNLOAD_TIMEOUT = get_config('DOWNLOAD_TIMEOUT')
CHUNK_SIZE = get_config('CHUNK_SIZE')
THUMB_HEIGHT = get_config('THUMB_HEIGHT', wrapper=int)
THUMB_WIDTH = get_config('THUMB_WIDTH', wrapper=int)
DATA_DIR = get_config('DATA_DIR')

Path(get_config('DATA_DIR')).mkdir(parents=True, exist_ok=True)

SUPPORTED_FORMATS = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'video/mp4': 'mp4',
    'video/mpeg': 'mpeg',
    'image/webp': 'webp',
    'video/webm': 'webm',
    'video/x-msvideo': 'avi'
}

SUPPORTED_EXTS = {val: key for key, val in SUPPORTED_FORMATS.items()}


class ImageException(Exception): pass  # noqa


class ImageDownloadException(ImageException): pass  # noqa


class ImageFileMissingException(ImageException): pass   # noqa


class ParsePath:

    @classmethod
    def parse(cls, path):
        if path[0] == '/':
            path = path[1:]
        parsed = path.split('/')
        pp = cls()
        pp.collection = parsed.pop(0)
        if len(parsed) > 1:
            pp.parent_dir = parsed.pop(0)
        pp.filename, pp.ext = parsed[-1].rsplit('.', 1)
        return pp

    def __init__(self, collection: str = None, parent_dir: str = None,
                 filename: str = None,
                 ext: str = None):
        self.collection = collection
        self.parent_dir = parent_dir
        self.filename = filename
        self.ext = ext

    def get_path(self, no_collection=False, no_parent=False, no_filename=False,
                 no_ext=False, no_thumb=True):
        res = []
        if not no_collection:
            res.append(self.collection)
        if not no_parent and self.parent_dir:
            res.append(self.parent_dir)
        if not no_thumb:
            res.append('.thumb')
        if not no_filename:
            if not no_ext:
                res.append(f'{self.filename}.{self.ext}')
            else:
                res.append(self.filename)
        return '/'.join(res)

    def __repr__(self):
        return str(self.__dict__)


class Image:
    DATA_DIR = get_config('DATA_DIR')

    STATE_CREATED = 'created'
    STATE_DOWNLOADED = 'downloaded'
    STATE_READY = 'ready'

    @staticmethod
    def get_uuid_from_link(link):
        _, uuid, cuuid = link.split(':', 2)
        return f'{uuid}:{cuuid}' if cuuid != '@' else uuid

    @staticmethod
    def get_filename_from_url_link(url) -> dict:
        url = urllib.parse.unquote(url).lower()
        if match := re.match(
                r'(?P<path>.*)/(?P<filename>[^\/\?]+)(\?.*)?$', url):
            parsed = match.groupdict()
            filename = parsed.get('filename', '')
            if filename.isdigit() and parsed.get('path'):
                filename = os.path.basename(parsed.get('path'))
            if (last_dot := filename.rfind('.')) > -1:
                ext = filename[last_dot+1:]
                if ext in SUPPORTED_EXTS:
                    return filename[0:last_dot], ext
            return filename, None
        return None, None

    @staticmethod
    def get_unique_filename(path: str | ParsePath, filename: str = None,
                            ext: str = None) -> str:
        if isinstance(path, ParsePath):
            filename = path.filename
            ext = path.ext
            path = path.get_path(no_filename=True)
        ix = 0
        it = ''
        test_name = f'{path}/{filename}{it}.{ext}'
        while os.path.exists(f'{Image.DATA_DIR}/{test_name}'):
            it = f'-{ix}'
            ix += 1
            test_name = f'{path}/{filename}{it}.{ext}'
        return test_name

    @classmethod
    async def get(cls, image_request: ImageRequest, db: RedisManager,
                  with_matrix=False):
        if image_request.filename:
            query = Query(
                f'@filename:({image_request.full_filename.replace("-", "?")})'
            ).dialect(2)
            result = await db.ix_images.search(query)
            if result.total == 0:
                return None
            data = None
            for it in result.docs:
                if it.filename == image_request.full_filename:
                    data = it.__dict__
            if not data:
                return None
            data.pop('payload')  # Default result of search
            data['uuid'] = cls.get_uuid_from_link(data.pop('id'))
            logger.info(f'Load image {data["uuid"]}')
            # if 'matrix' in data and not with_matrix:
            #     data.pop('matrix')
            data = dict_bytes2str(data)
            return Image(**data)
        elif image_request.uuid:
            data = await db.r.hgetall(image_request.redis_link)
            if not data:
                keys = await db.r.keys(f'images:*:{image_request.uuid}')
                if keys:
                    data = await db.r.hgetall(keys[0])
                    logger.info(f'Load image {data["uuid"]}')
                else:
                    # Search by original uuid
                    query2 = Query(
                        f'@original_uuid:({image_request.uuid})'
                    ).dialect(2)
                    result2 = await db.ix_images.search(query2)
                    if result2.total == 0:
                        return None
                    data = result2.docs[0].__dict__
                    data.pop('payload')  # Default result of search
                    data['uuid'] = cls.get_uuid_from_link(data.pop('id'))
                    logger.info(f'Load image {data["uuid"]} by original link'
                                f' {image_request.uuid}')
            data = dict_bytes2str(data)
            if 'uuid' not in data:
                data['uuid'] = image_request.full_uuid
            return Image(**data)
        else:
            return None

    @classmethod
    async def download(cls, image_request: ImageRequest, **kwargs):
        img = Image(
            url=image_request.url,
            uuid=image_request.full_uuid,
            state=cls.STATE_CREATED,
            created=datetime.datetime.now().timestamp(),
            collection=image_request.collection,
            _parent=kwargs.get('parent')
        )
        await img.redownload(user_agent=kwargs.get('user_agent'))
        return img

    async def redownload(self, **kwargs):
        params = {
            'img': self,
            '_headers': {
                'User-Agent': kwargs.get('user_agent') or DEFAULT_USER_AGENT
            }
        }
        rewrite = True
        if not (url := kwargs.get('url')):
            await Plugin.run(Plugin.EVENT_PARSE_URL, params)
            url = self.url
            rewrite = False
        async with (aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)) as session):
            async with session.get(
                    url,
                    headers=params['_headers'],
                    timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)
            ) as response:
                logger.info(response.headers.items())
                self.content_type = response.headers.get('content-type')
                if self.content_type and \
                        self.content_type not in SUPPORTED_FORMATS:
                    raise ImageDownloadException(
                        f"The format of the downloading file "
                        f"'{url}' is not supported. "
                        f"(content-type: {self.content_type})")
                self.size = response.content_length
                if not rewrite:
                    filename, ext = self.get_filename_from_url_link(url)
                    know_type = SUPPORTED_EXTS.get(ext, None)
                    if not self.content_type:
                        self.content_type = SUPPORTED_EXTS.get(ext, None)
                    elif know_type != self.content_type:
                        # Fix file extension
                        new_ext = SUPPORTED_FORMATS.get(self.content_type)
                        logger.info(
                            f"The image has got wrong file "
                            f"extension {ext} -> {new_ext}")
                        ext = new_ext
                    path = self.collection if self.collection != '@' \
                        else datetime.date.today().year
                    if self._parent:
                        path = ParsePath.parse(self._parent.filename).get_path(
                            no_ext=True, no_parent=True)
                    self.filename = self.get_unique_filename(path, filename,
                                                             ext)
                    self.make_folder()
                    if not self.title:
                        self.title = re.sub(
                            r'[_-]', ' ', filename
                        ).capitalize()

                fd = await async_open(self.full_path, 'w+b')
                async for data in response.content.iter_any():
                    await fd.write(data)
                await fd.close()
                return True

    def __init__(self, **kwargs):
        self.uuid = None
        self.url = None
        self.title = None
        self.content_type = None
        self.size = 0
        self.filename = None
        self.thumb_created = None
        self.thumb_file = None
        self.state = None
        self.width = 0
        self.height = 0
        self.collection = '@'
        self.url = None
        self._parent = None
        self.original_uuid = ''
        for key in ['width', 'height', 'size']:
            if key in kwargs:
                kwargs[key] = int(kwargs[key])
        self.__dict__.update(kwargs)

    @property
    def full_path(self) -> str:
        return f'{self.DATA_DIR}/{self.filename}'

    @property
    def full_thumb_image_path(self) -> str:
        if self.thumb_file:
            return f'{DATA_DIR}/{self.thumb_file}'
        _dir, _file = self.full_path.rsplit('/', 1)
        return f'{_dir}/.thumb/{_file}'

    @property
    def is_file_exist(self) -> bool:
        return os.path.exists(self.full_path)

    @property
    def data(self):
        return {key: val for key, val in self.__dict__.items() if
                val and not key.startswith('_')}

    @property
    def is_main_image(self) -> bool:
        return ':' not in self.uuid

    @property
    def uuid_parts(self):
        return self.uuid.split(':', 1)

    def add_url_reference(self, url):
        self.add_uuid_reference(ImageRequest.make_uuid(url))

    def add_uuid_reference(self, uuid):
        hashes = set(self.original_uuid.split(';')
                     if self.original_uuid else [])
        if uuid not in hashes:
            hashes.add(uuid)
        if self.uuid in hashes:
            hashes.remove(self.uuid)
        self.original_uuid = ';'.join(hashes)

    def make_folder(self):
        (Path(os.path.dirname(self.full_path))
         .mkdir(parents=True, exist_ok=True))
        (Path(os.path.dirname(self.full_thumb_image_path))
         .mkdir(parents=True, exist_ok=True))

    def delete_empty_folders(self, file):
        folder = os.path.dirname(file)
        t_folder = f'{folder}/.thumb'
        try:
            if not os.listdir(t_folder):
                Path(t_folder).rmdir()
                Path(folder).rmdir()
                logger.info(f"The folder {folder} was empty and "
                            f"it is deleted.")
        except Exception:
            pass

    async def get_all_alternates(self, db: RedisManager) -> ['Image']:
        uuids = self.uuid.split(':', 1)
        keys = await db.r.keys(f'images:{uuids[0]}:*')
        res = []
        for key in keys:
            if key[-1] != '@':
                data = await db.r.hgetall(key)
                if data:
                    # TODO: remove after clean up DB
                    data['uuid'] = ImageRequest(redis_channel=key).full_uuid
                    res.append(Image(**data))
        return sorted(res, key=lambda x: x.created)

    async def get_content_chunks(self, chunk=None):
        if not self.is_file_exist:
            raise ImageFileMissingException('File missing', code=404)
        async with async_open(self.full_path, 'rb') as fd:
            async for data in fd.iter_chunked(chunk or CHUNK_SIZE):
                yield data

    async def make_thumb(self, db: RedisManager, force=False):
        if not os.path.exists(self.full_thumb_image_path) or force:
            logger.info(f"Making thumb image for {self.filename}")
            task = ImageTask().set_action(
                uuid=self.uuid,
                cmd='resize',
                width=THUMB_WIDTH,
                height=THUMB_HEIGHT,
                thumb=True
            )
            await task.save(db)
            time.sleep(.5)
            if self.collection and self.collection != '@':
                task2 = ImageTask().set_action(
                    collection=self.collection,
                    cmd='make_gif_from_images',
                    width=THUMB_WIDTH,
                    height=THUMB_HEIGHT,
                    thumb=True
                )
                await task2.save(db)

    async def save(self, db: RedisManager, pipe=None):
        if not pipe:
            pipe = db.r
        alternate = ':@' if self.is_main_image else ''
        topic = f'images:{self.uuid}{alternate}'
        await pipe.hset(topic, mapping={k: v for k, v in self.data.items() if
                                        k != 'uuid'})

    async def delete(self, db: RedisManager):
        topic = f'images:{self.uuid}'
        oi = self.original_uuid.split(';') if self.original_uuid else []
        original_uuids = [ImageRequest.make_uuid(self.url), *oi]
        alternates = await self.get_all_alternates(db)
        uuids = self.uuid.split(':')
        _uuid = uuids[-1]
        if self.is_main_image:
            _uuid = uuids[0]
            topic = f'{topic}:@'
            if alternates:
                # set another alternate as main
                if res := await alternates[0].set_as_main(db):
                    topic = f'images:{res["original_main"]}'
                    await asyncio.sleep(.5)
        await db.r.delete(topic)
        await db.r.delete(f'matrix:{_uuid}')
        os.path.exists(self.full_path) and os.unlink(self.full_path)
        os.path.exists(self.full_thumb_image_path) and os.unlink(
            self.full_thumb_image_path)
        new_main = await Image.get(ImageRequest(uuid=uuids[0]), db=db)
        [new_main.add_uuid_reference(u) for u in original_uuids]
        await new_main.save(db)
        if len(alternates) == 1:
            # The image is only one - no alternates
            await new_main.move_from_own_subfolder(db)

        self.delete_empty_folders(self.full_path)
        if self.is_main_image and self.collection != '@':
            task = ImageTask().set_action(
                collection=self.collection,
                cmd='make_gif_from_images',
                width=THUMB_WIDTH,
                height=THUMB_HEIGHT,
                thumb=True
            )
            await task.save(db)

    async def move_to_own_subfolder(self, db):
        org_filename = self.full_path
        org_thumb = self.full_thumb_image_path
        path = ParsePath.parse(self.filename)
        path.parent_dir = path.filename
        self.filename = self.get_unique_filename(path)
        self.make_folder()
        os.rename(org_filename, self.full_path)
        os.rename(org_thumb, self.full_thumb_image_path)
        await self.save(db)

    async def move_from_own_subfolder(self, db):
        org_filename = self.full_path
        org_thumb = self.full_thumb_image_path
        path = ParsePath.parse(self.filename)
        path.parent_dir = None
        self.filename = self.get_unique_filename(path)
        self.make_folder()
        os.rename(org_filename, self.full_path)
        os.rename(org_thumb, self.full_thumb_image_path)
        self.delete_empty_folders(org_filename)
        await self.save(db)

    def __move_files(self, collection):
        org_filename = self.full_path
        org_thumb = self.full_thumb_image_path
        path = ParsePath.parse(self.filename)
        path.collection = collection
        self.filename = self.get_unique_filename(path)
        self.make_folder()
        os.rename(org_filename, self.full_path)
        os.rename(org_thumb, self.full_thumb_image_path)
        self.delete_empty_folders(org_filename)

    async def set_collection(self, db: RedisManager, collection, pipe=None):
        async def __process(pipe, coll):
            # Update this image
            self.collection = coll.name
            self.__move_files(coll.name)
            await self.save(None, pipe)
            if self.is_main_image:
                # Update alternates
                alternates = await self.get_all_alternates(db)
                for aimage in alternates:
                    await aimage.set_collection(None, coll, pipe)

        old_collection_name = self.collection
        if pipe:
            await __process(pipe, collection)
            return
        async with db.r.pipeline(transaction=True) as pipe:
            pipe.multi()
            await __process(pipe, collection)
            await pipe.execute()
        if self.is_main_image:
            if collection.name != '@':
                await collection.make_thumb(db, True)
            if old_collection_name != '@':
                old_collection = await Collection.get(old_collection_name, db)
                await old_collection.make_thumb(db, True)

    async def set_as_main(self, db: RedisManager):
        if self.is_main_image:
            return
        # parent_uuid, child_uuid = self.uuid.split(':', 1)
        old_main: Image = await Image.get(
            ImageRequest(uuid=self.uuid_parts[0]), db)
        res = {}
        async with db.r.pipeline(transaction=True) as pipe:
            pipe.multi()
            if old_main:
                iro = ImageRequest(parent_uuid=old_main.uuid_parts[0],
                                   url=old_main.url)
                iro.update_uuid()
                await pipe.rename(f'images:{old_main.uuid}:@',
                                  f'images:{iro.full_uuid}')
                res['original_main'] = iro.full_uuid
            await pipe.rename(f'images:{self.uuid}',
                              f'images:{self.uuid_parts[0]}:@')
            await pipe.execute()
        return res

    async def set_as_alternation_of(self, image: 'Image', db: RedisManager):
        org_uuid = self.uuid_parts
        self.uuid = f'{image.uuid_parts[0]}:{self.uuid_parts[-1]}'
        org_filename = self.full_path
        org_thumb = self.full_thumb_image_path
        path = ParsePath.parse(self.filename)
        path.parent_dir = ParsePath.parse(image.filename).filename
        self.filename = self.get_unique_filename(path)
        self.make_folder()
        os.rename(org_filename, self.full_path)
        os.rename(org_thumb, self.full_thumb_image_path)
        self.delete_empty_folders(org_filename)
        async with db.r.pipeline(transaction=True) as pipe:
            pipe.multi()
            if len(org_uuid) == 1:
                org_uuid.append('@')
            await pipe.rename(
                f'images:{":".join(org_uuid)}',
                f'images:{self.uuid}')
            await self.save(None, pipe)
            await pipe.execute()


class AlternateImage(Image):

    @classmethod
    def create_from_image(cls, image: Image, **kwargs) -> 'AlternateImage':
        sub_uuid = kwargs.get('sub_uuid')
        if not sub_uuid:
            sub_uuid = str(
                hashlib.md5(repr(sorted(kwargs.items())).encode()).hexdigest())

        path = ParsePath.parse(image.filename)
        path.ext = kwargs.get('format', path.ext)
        path.filename = kwargs.get('filename', path.filename)
        filename = path.get_path(no_thumb=kwargs.get('thumb') is None)
        return AlternateImage(
            uuid=f'{image.uuid}:{sub_uuid}',
            filename=filename,
            mutation=json.dumps(kwargs),
            state=Image.STATE_CREATED,
            content_type=SUPPORTED_EXTS[path.ext],
            width=image.width,
            height=image.height
        )
