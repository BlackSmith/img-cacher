import os

from aiohttp import web
from aiohttp.abc import Request
from aiohttp.web_response import Response, StreamResponse
from aiohttp.web_runner import GracefulExit
from loggate import get_logger, setup_logging

from libs import get_yaml
from config import get_config
from libs.redis_manager import RedisManager
from libs.socket_manager import SocketManager
from modules.image_request_parser import ImageRequest

logging_profiles = get_yaml(get_config('LOGGING_DEFINITIONS'))
setup_logging(profiles=logging_profiles)

from config import get_config
from modules.collection import Collection
from modules.image import Image, ImageDownloadException
from modules.user_manager import UserManager

# Next is required
from modules.image_task import ImageTask  # noqa
from modules.image_manager import ImageManager  # noqa
from modules.plugins.tineye import TineyePlugin  # noqa
from modules.plugins.yandex import YandexPlugin     # noqa

DATA_DIR = get_config('DATA_DIR')
HOST_URL = get_config('HOST_URL')

routes = web.RouteTableDef()
logger = get_logger('main')


async def on_startup(app: web.Application):
    try:
        app['redis'] = RedisManager(get_config('REDIS_URI'), app=app)
        await app['redis'].connection()
        await UserManager.create_accounts_by_env(app['redis'])
    except Exception as ex:
        logger.error(ex)
        raise GracefulExit()
    #     await app.shutdown()
    #     await app.cleanup()


async def on_cleanup(app):
    if app.get('redis'):
        await app['redis'].disconnect()


@routes.get("/favicon.ico")
async def favicon(request: Request) -> Response:
    with open('static/favicon.ico', 'rb') as favicon_file:
        favicon = favicon_file.read()
    return web.Response(body=favicon, content_type='image/x-icon')


@routes.get(r"/{path:.*/\.thumb/[^/]+}")
async def thumb(request: Request) -> Response:
    thumb_filename = request.match_info.get('path')
    logger.debug(f'Open thumb image {thumb_filename}')
    if os.path.exists(f'{DATA_DIR}/{thumb_filename}'):
        with open(f'{DATA_DIR}/{thumb_filename}', 'rb') as fd:
            image_data = fd.read()
        response = web.Response(
            body=image_data
        )
    else:
        db = request.app["redis"]
        irp = ImageRequest(request=request)
        if not irp.uuid and irp.collection and irp.filename.startswith(
                irp.collection):
            collection = await Collection.get(irp.collection, db=db)
            await collection.make_thumb(db)
        else:
            img = await Image.get(irp, db=db)
            if img:
                await img.make_thumb(db)
        response = web.Response(reason='Thumb is not ready. Try it later.',
                                status=307)
    return response


@routes.get('/')
@routes.get('/collections/')
@routes.get(r'/{path:collections/[^\/]+/?}')
async def index(request: Request):
    if request.query.get('url') and (
            request.match_info.get('path') or request.path == '/'):
        return await root(request)
    return web.FileResponse('static/index.html')


@routes.get("/{path:.+}")
async def root(request: Request) -> Response:
    db = request.app["redis"]
    irp = ImageRequest(request=request)
    img = await Image.get(irp, db=request.app["redis"])
    if irp.url:
        if img and not irp.was_uuid_generated:
            logger.info(
                f"Downloading alternate image {irp.url} as "
                f"alternate image for {img.filename}.")
            try:
                irp.update_uuid()
                irp.parent_uuid = img.uuid
                a_img = await Image.download(irp, parent=img,
                                             user_agent=request.headers.get(
                                                 'User-Agent'))
                await a_img.save(db)
                await a_img.make_thumb(db)
                await img.move_to_own_subfolder(db)
                img = a_img
            except ImageDownloadException as ex:
                return Response(text=str(ex), status=500)
        elif not img:
            logger.info(
                f"Downloading image {irp.url} to collection {irp.collection}.")
            try:
                img = await Image.download(irp, user_agent=request.headers.get(
                    'User-Agent'))
                await img.save(db)
                await img.make_thumb(db)
            except ImageDownloadException as ex:
                return Response(text=str(ex), status=500)
    if not img:
        return Response(text="The image was not found.", status=404)
    if request.query.get('ui', False) or request.query.get('webui', False):
        return web.FileResponse('static/index.html')
    response = StreamResponse()
    response.content_type = img.content_type
    response.content_length = img.size
    response.headers[
        'Content-Disposition'] = (f'inline; filename="'
                                  f'{os.path.basename(img.filename)}"')
    await response.prepare(request)
    async for data in img.get_content_chunks():
        await response.write(data)
    await response.write_eof()
    return response


async def on_prepare(request, response):
    response.headers['Access-Control-Allow-Origin'] = '*'


app = web.Application()  # Main application
msocket = SocketManager()

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)
app.router.add_get('/ws', msocket.websocket_handler)
app.router.add_static('/static/', path='static/', name='static')
app.router.add_static('/assets/', path='static/assets/', name='assets')
app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)
