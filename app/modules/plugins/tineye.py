import os

import aiohttp
from loggate import get_logger

from config import get_config
from libs.socket_manager import socket_command
from libs.helper import login_required
from modules.image import Image
from modules.image_request_parser import ImageRequest

HOST_URL = get_config('HOST_URL')
DEFAULT_USER_AGENT = get_config('DEFAULT_USER_AGENT')
logger = get_logger('TineyePlugin')


class TineyePlugin:
    URL = 'https://tineye.com/result_json/'
    HEADERS = {
        'User-Agent': DEFAULT_USER_AGENT,
        'Origin': 'https://tineye.com'
    }

    @socket_command('get_tineye_links')
    @login_required
    @staticmethod
    async def get_tineye_links(payload, db, **kwargs):
        irp = ImageRequest(uuid=payload.get('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng'}
        res = await TineyePlugin.try_to_get_tineye_links(image)
        return {'status': 'ok', 'lines': res}

    @classmethod
    async def try_to_get_tineye_links(cls, image: Image):
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('image', open(image.full_path, 'rb'),
                               filename=os.path.basename(image.filename))
                async with session.post(cls.URL, data=data,
                                        headers=cls.HEADERS,
                                        timeout=aiohttp.ClientTimeout(
                                            total=60)) as response:
                    data = await response.json()
            return data.get('matches', [])
        except Exception as ex:
            logger.error(ex)
        return []
