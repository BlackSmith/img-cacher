import hashlib
import re
import urllib

from aiohttp.web_request import Request


class ImageRequest:

    @staticmethod
    def make_uuid(data) -> str:
        return hashlib.md5(data.encode()).hexdigest()

    def __init__(self, uuid: str = None, parent_uuid: str = None,
                 url: str = None, filename: str = None,
                 folder: str = None, collection: str = None,
                 request: Request = None,
                 redis_channel: str = None):
        self.uuid = uuid
        self.parent_uuid = parent_uuid
        if self.uuid and not self.parent_uuid and ':' in self.uuid:
            self.parent_uuid, self.uuid = self.uuid.split(':', 1)
        self.url = url
        self.filename = filename
        self.folder = folder
        self.collection = collection
        self.was_uuid_generated = False
        if request:
            self.__parse(request)
        if redis_channel:
            self.__parse_redis(redis_channel)

    @property
    def full_uuid(self) -> str:
        if self.parent_uuid:
            return ':'.join([self.parent_uuid, self.uuid])
        else:
            return self.uuid

    @property
    def redis_link(self) -> str:
        if not self.uuid:
            return ''
        return f'images:{self.uuid}:@' if not self.parent_uuid \
            else f'images:{self.full_uuid}'

    @property
    def full_filename(self):
        return f'{self.collection}/{self.filename}'

    @property
    def params(self) -> dict:
        res = {}
        if self.uuid:
            res['uuid'] = self.uuid
        if self.parent_uuid:
            res['parent_uuid'] = self.parent_uuid
        if self.url:
            res['url'] = self.url
        if self.filename:
            res['filename'] = self.filename
        if self.collection:
            res['collection'] = self.collection
        return res

    def update_uuid(self) -> bool:
        if self.url:
            self.uuid = self.make_uuid(self.url)
            self.was_uuid_generated = True
            return True
        return False

    def __repr__(self):
        return str(self.params)

    def __parse_redis(self, channel):
        # '__keyspace@1__:images:57885c2e786813868fe46f626079d4fe:@'
        if match := re.match(
                r'.*:?images:(?P<parent>[0-9a-f]+)'
                r'(:((?P<child>[0-9a-f]+)|@))?', channel):
            child = match.group('child')
            if child:
                self.uuid = child
                self.parent_uuid = match.group('parent')
            else:
                self.uuid = match.group('parent')

    def __parse(self, request):
        path = request.match_info.get('path') or ''
        # UUID
        if match := re.match(
                r'^(|collections/(?P<collection>[^/:]+)/?|'
                r'((?P<parent>[0-9a-f]{10,})(:(?P<child>[0-9a-f]{10,}))?))$',
                path, re.I):
            self.collection = match.group('collection') or '@'
            child_uuid = match.group('child')
            if child_uuid:
                self.uuid = child_uuid
                self.parent_uuid = match.group('parent')
            else:
                self.uuid = match.group('parent')
        elif '/' in path:
            # filename
            path = path.replace('.thumb/', '')
            self.collection, self.filename = path.split('/', 1)
        if match := re.match(r'.*&?url=(?P<url>.*)$',
                             request.query_string):
            self.url = urllib.parse.unquote(match.group('url'))
            if not self.uuid:
                self.uuid = hashlib.md5(self.url.encode()).hexdigest()
                self.was_uuid_generated = True
