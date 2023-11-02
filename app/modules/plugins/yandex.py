import json
import os

import aiohttp
from bs4 import BeautifulSoup
from loggate import get_logger

from config import get_config
from libs.helper import login_required
from libs.socket_manager import socket_command
from modules.image import Image
from modules.image_request_parser import ImageRequest

HOST_URL = get_config('HOST_URL')
LOCAL_HOSTNAME = 'localhost' in HOST_URL or '127.0.0.1' in HOST_URL
DEFAULT_USER_AGENT = get_config('DEFAULT_USER_AGENT')
logger = get_logger('YandexPlugin')


class YandexPlugin:
    REQUEST_URL = ('https://www.yandex.com/images/touch/search?rpt=imageview'
                   '&format=json&request='
                   '{"blocks":[{"block":"cbir-uploader__get-cbir-id"}]}')
    RESPONSE_URL = 'https://www.yandex.com/images/search'
    HEADERS = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Host': 'www.yandex.com',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br'
    }

    @socket_command('get_yandex_links')
    @login_required
    @staticmethod
    async def get_yandex_links(payload, db, **kwargs):
        irp = ImageRequest(uuid=payload.get('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng'}
        return await YandexPlugin.try_to_get_yandex_links(image)
        return

    @classmethod
    async def try_to_get_yandex_links(cls, image: Image):
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('upfile',
                               open(image.full_path, 'rb'),
                               filename=os.path.basename(image.filename))
                async with session.post(
                        cls.REQUEST_URL, data=data, headers=cls.HEADERS,
                        timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if res := await response.json():
                        url = (f'{cls.RESPONSE_URL}?'
                               f'{res["blocks"][0]["params"]["url"]}')
                        logger.info(f'Response url: {url}')
                        async with session.get(
                                cls.RESPONSE_URL,
                                params=res["blocks"][0]["params"]["url"],
                                headers=cls.HEADERS,
                                timeout=aiohttp.ClientTimeout(total=30)
                        ) as page:
                            page.raise_for_status()
                            data = cls.parse_page(await page.text())
                            data['response_url'] = url
                            return {'status': 'ok', 'response': data}
        except (aiohttp.client_exceptions.ClientOSError,
                aiohttp.client_exceptions.ServerDisconnectedError):
            if not LOCAL_HOSTNAME:
                try:
                    async with (aiohttp.ClientSession() as session):
                        logger.info("Pushing image failed, we try backup way.")
                        params = {'source': 'collections',
                                  'rpt': 'imageview',
                                  'url': f'{HOST_URL}/{image.filename}'}
                        async with session.get(
                                cls.RESPONSE_URL,
                                params=params,
                                headers=cls.HEADERS,
                                timeout=aiohttp.ClientTimeout(total=30)
                        ) as page:
                            page.raise_for_status()
                            data = cls.parse_page(await page.text())
                            return {'status': 'ok', 'response': data}
                except Exception:
                    pass
            return {'status': 'ng', 'response': {'error': 'Connection erorr.'}}
        except Exception as ex:
            logger.error(ex, exc_info=ex)
            raise ex

    @staticmethod
    def parse_page(page):
        res = {
            'sites': [],
            'similar': {}
        }
        soup = None
        try:
            soup = BeautifulSoup(page, 'html.parser')
            blocks = soup.findAll('div', class_='Root')
            if not blocks:
                res[
                    'erorr'] = ("Loading data from Yandex failed. "
                                "Please open link directly.")
                return res
            for block in blocks:
                if block['id'].startswith('CbirSimilar'):
                    res['similar'] = json.loads(block['data-state'])
                    for rec in res['similar']['thumbs']:
                        if rec['imageUrl'].startswith('//'):
                            rec['imageUrl'] = f'https:{rec["imageUrl"]}'
                        if rec['linkUrl'].startswith('/'):
                            rec['linkUrl'] = \
                                f'https://www.yandex.com{rec["linkUrl"]}'
                elif block['id'].startswith('CbirSites'):
                    res['sites'] = json.loads(block['data-state'])
            return res
        except Exception as ex:
            logger.error(ex, exc_info=ex)
        return res
