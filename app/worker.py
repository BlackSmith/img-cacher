import asyncio
import os

os.environ['APP_TYPE'] = 'worker'

from modules.image_manager import ImageManager  # noqa

from loggate import setup_logging, get_logger
from config import get_config

from libs import get_yaml
from libs.redis_manager import RedisManager, redis_subscribe
from modules.image_task import ImageTask
from modules.actions.image_actions import ImageActions
from modules.actions.video_actions import VideoActions
from modules.collection import Collection
from modules.image import Image
from modules.image_request_parser import ImageRequest

logging_profiles = get_yaml(get_config('LOGGING_DEFINITIONS'))
setup_logging(profiles=logging_profiles)
logger = get_logger('main')

is_init_redis_done = False


async def graceful_shutdown(loop, sig=None):
    """Cleanup tasks tied to the service's shutdown."""
    if sig:
        logger.info(f"Received exit signal {sig.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not
             asyncio.current_task()]
    [task.cancel() for task in tasks]
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        loop.stop()


def handle_exception(loop, context):
    logger.error(f'{context["future"]}')
    print(context.get('exception', ''))
    loop.create_task(graceful_shutdown(loop), name="tasks/shutdown")


async def run_task(db: RedisManager, task: ImageTask):
    logger.info(f"Run task: {task.__dict__}")
    cmd = task.action.get('cmd')
    if uuid := task.action.get('uuid'):
        irp = ImageRequest(uuid=uuid)
        image = await Image.get(irp, db)
        if not image:
            await task.set_error(
                db,
                'The image does not exist (uuid: {irp.uuid})'
            )
            return
        action_class = ImageActions if image.content_type.startswith(
            'image') else VideoActions
        try:
            fce = getattr(action_class, cmd)
            if await fce(image, **task.action, db=db):
                await task.set_done(db)
        except Exception as ex:
            await task.set_error(db, str(ex))
        return
    elif col_name := task.action.get('collection'):
        collection: Collection = await Collection.get(col_name, db)
        images = await collection.get_members(db, 0, 25)
        if cmd == 'make_gif_from_images' and images:
            if await ImageActions.make_gif_from_images(
                    images,
                    db=db,
                    collection=collection,
                    **{k: v for k, v in task.action.items() if
                       k not in ['collection']}):
                await task.set_done(db)
                return
    await task.set_error(db, 'Unknown action')


@redis_subscribe('__key*__:tasks:*', 'worker')
async def redis_watcher(channel: str, action: str, db: RedisManager, **kwargs):
    global is_init_redis_done
    if not is_init_redis_done:
        return
    _, task_uuid = channel.rsplit(':', 1)
    if task_uuid:
        task_uuid = f'tasks:{task_uuid}'
        task = await ImageTask.take_ready_task(db, task_uuid)
        if task:
            await run_task(db, task)


async def redis_init(db: RedisManager):
    """
    Run after start and do all incomplete tasks.
    :param db:
    :return:
    """
    try:
        while task := await ImageTask.take_ready_task(db):
            await run_task(db, task)
        global is_init_redis_done
        is_init_redis_done = True
    except asyncio.CancelledError:
        pass


def main():
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    db = RedisManager(get_config('REDIS_URI'), {})
    loop.run_until_complete(db.connection())
    loop.run_until_complete(redis_init(db))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(db.disconnect())


if __name__ == "__main__":
    main()
