import datetime

from loggate import get_logger

from moviepy.video.io.VideoFileClip import VideoFileClip

from moviepy.video.fx import resize as fx_resize
from config import get_config
from libs.redis_manager import RedisManager
from modules.actions import Action, ImageActionException
from modules.image import Image, AlternateImage

logger = get_logger('VideoActions')
DATA_DIR = get_config('DATA_DIR')


class VideoActions(Action):
    TYPE = 'video'

    @classmethod
    async def update_metadata(cls, image: Image, db: RedisManager,
                              **kwargs) -> Image:
        if not image.is_file_exist:
            logger.error(
                f"I can not update metadata, the image "
                f"{image.full_path} does not exist.")
            return
        video = VideoFileClip(image.full_path)
        image.width, image.height = video.size
        video.close()
        await image.save(db)
        return True

    @classmethod
    async def resize(cls, image: Image, db: RedisManager, **kwargs) -> Image:
        if not image.width or not image.height:
            await cls.update_metadata(image, db)
        if kwargs.get('thumb') and not kwargs.get('format'):
            kwargs['format'] = 'gif'
        a_image = AlternateImage.create_from_image(image, **kwargs)
        a_image.make_folder()
        a_image.width, a_image.height = \
            cls.calculation_size(image.width, image.height,
                                 int(kwargs.get('width', 0)),
                                 int(kwargs.get('height', 0)))

        if not a_image.width and not a_image.height:
            raise ImageActionException(
                'Resizing requires width and height parameter.')

        video_clip = VideoFileClip(image.full_path)
        gif_clip = video_clip.subclip(0, 5) \
            .fx(fx_resize.resize, (a_image.width, a_image.height))
        logger.info(
            f"The video {image.filename} was resized "
            f"({a_image.width}x{a_image.height}) to {a_image.filename}")
        gif_clip.write_gif(a_image.full_path)
        video_clip.close()
        if kwargs.get('thumb'):
            image.thumb_created = datetime.datetime.now().timestamp()
            image.thumb_file = a_image.filename
            await image.save(db)
            return True
        await a_image.save(db)
        return True
