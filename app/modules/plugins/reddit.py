import re

import aiohttp

from .plugin import Plugin
from libs import dicts_val, normalize_filename


# https://www.reddit.com/r/nsfw/comments/18n3n2e/apples/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
# https://www.reddit.com/r/nsfw/comments/18n3n2e/apples/?utm_source=share&utm_content=share_button
# https://www.reddit.com/r/nsfw/comments/18n3n2e/apples/?utm_source=share
# https://www.reddit.com/r/nsfw/comments/18n3n2e/apples/

class RedditPlugin(Plugin):

    @classmethod
    def get_callbacks(cls):
        return {
            cls.EVENT_PARSE_URL: cls.parse_url
        }

    @staticmethod
    async def parse_url(action: str, params: dict):
        img = params['img']
        url = img.url
        try:
            if url.startswith('https://i.redd.it/'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            f'https://www.reddit.com/media?url={url}',
                            headers=params['_headers'],
                            timeout=aiohttp.ClientTimeout(
                                total=10)) as response:
                        response.raise_for_status()
                        page = await response.read()
                        rex = (r'(?P<url>https://www\.reddit\.com/'
                               r'[^&]+/comments/[^&]+/)')
                        if match := re.search(
                                rex,
                                page.decode(encoding="ascii", errors="ignore"),
                                re.M):
                            url = match.group('url')
        except Exception:
            pass
        if url.startswith('https://www.reddit.com/'):
            # Fix: Someone remove this parameter from url and images are cached
            # twice.
            img.add_url_reference(url.replace('&utm_medium=web2x', ''))
            path, _ = url.rsplit('/', 1)
            async with aiohttp.ClientSession() as session:
                json_url = f'{path}.json'
                async with session.get(json_url, headers=params['_headers'],
                                       timeout=aiohttp.ClientTimeout(
                                           total=10)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    data = dicts_val('0.data.children.0.data', data)
                    img.json_url = json_url
                    img.url = data['url']
                    img.add_url_reference(data['url'])
                    img.title = data.get('title')
                    img.filename = normalize_filename(data.get('title'))
                    img.reddit_score = data.get('score', 0)
                    video_info = dicts_val('preview.reddit_video_preview',
                                           data, default=None)
                    if video_info:
                        img.url = video_info['fallback_url']
                        img.add_url_reference(video_info['fallback_url'])
                        img.height = video_info.get('height')
                        img.width = video_info.get('width')
                        img.bitrate_kbps = video_info.get('bitrate_kbps')
                        img.duration = video_info.get('duration')
                        img.thumbnail = dicts_val('media.oembed.thumbnail_url',
                                                  data, default=None)
