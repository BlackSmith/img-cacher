import asyncio
import datetime
import json
import math
import os.path
import pickle
from pathlib import Path

import cv2
import imageio
from loggate import get_logger

from config import get_config
from libs.redis_manager import RedisManager
from modules.actions import Action, ImageActionException
from modules.collection import Collection
from modules.image import Image, AlternateImage
from PIL import Image as PilImage

from modules.image_task import ImageTask

logger = get_logger('ImageActions')
DATA_DIR = get_config('DATA_DIR')


class ImageActions(Action):
    TYPE = 'image'
    DESCRIPTIONS = {}

    @classmethod
    async def update_metadata(cls, image: Image, db: RedisManager,
                              **kwargs) -> Image:
        if not image.is_file_exist:
            logger.error(f"I can not update metadata, the image "
                         f"{image.full_path} does not exist.")
            return False
        if not image.width or not image.height:
            with PilImage.open(image.full_path) as img:
                image.width, image.height = img.size
        await image.save(db)
        return True

    @classmethod
    async def resize(cls, image: Image, db: RedisManager, **kwargs) -> Image:
        if not image.width or not image.height:
            await cls.update_metadata(image, db)
        a_image = AlternateImage.create_from_image(image, **kwargs)
        a_image.make_folder()
        a_image.width, a_image.height = \
            cls.calculation_size(image.width, image.height,
                                 int(kwargs.get('width', 0)),
                                 int(kwargs.get('height', 0)))
        if not a_image.width and not a_image.height:
            raise ImageActionException(
                'Resizing requires width and height parameter.')

        with PilImage.open(image.full_path) as img:
            if image.content_type == 'image/gif':
                n_frames = img.n_frames
                fps = img.info.get('duration', 100)
                # if img.mode != 'RGB':
                #     img = img.convert('RGB')
                resized_frames = []
                for frame_number in range(n_frames):
                    img.seek(frame_number)
                    resized_frame = img.resize((a_image.width, a_image.height))
                    resized_frames.append(resized_frame)

                # self.thumb_image = f'{self.uuid}/thumb.{ext}'
                resized_frames[0].save(
                    a_image.full_path,
                    save_all=True,
                    append_images=resized_frames[1:],
                    duration=int(fps),
                    loop=img.info['loop']
                )
            else:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.resize((a_image.width, a_image.height)).save(
                    a_image.full_path)
        logger.info(
            f"The image {image.filename} was resized "
            f"({a_image.width}x{a_image.height}) to {a_image.filename}")
        if kwargs.get('thumb'):
            image.thumb_created = datetime.datetime.now().timestamp()
            await image.save(db)
            task = ImageTask(
                action={'uuid': image.uuid, 'cmd': 'find_same_images'})
            await task.save(db)
        else:
            await a_image.save(db)
        return True

    @classmethod
    async def make_gif_from_images(cls, images: list, db: RedisManager,
                                   collection: Collection = None, **kwargs):
        res = []
        max_width, max_height = int(kwargs.get('width', 0)), int(
            kwargs.get('height', 0))
        #
        for image in images:
            imgO = Image(**image)
            if not imgO.is_file_exist:
                continue
            img = PilImage.open(imgO.full_thumb_image_path)
            # n_frames = getattr(img, 'n_frames', 0)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # if imgO.content_type == 'image/gif':
            #     img = img.n_frames[math.ceil(n_frames/2)]
            c_width, c_height = int(image['width']), int(image['height'])
            width, height = cls.calculation_size(c_width, c_height, max_width,
                                                 max_height)
            if width != c_width or height != c_height:
                img.resize((width, height))
            centered_image = PilImage.new('RGBA', (max_width, max_height),
                                          (0, 0, 0, 0))
            x, y = math.ceil((max_width - width) / 2), math.ceil(
                (max_height - height) / 2)
            centered_image.paste(img, (x, y))
            res.append(centered_image)

        if res and collection:
            logger.info(f"{collection.name}'s thumb was made from "
                        f"{len(res)} pictures.")
            collection.thumb_file = (f'{collection.name}/.thumb/'
                                     f'{collection.name}.gif')
            Path(os.path.dirname(collection.full_thumb_image_path)).mkdir(
                parents=True, exist_ok=True)
            # gif = PilImage.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
            res[0].save(collection.full_thumb_image_path, save_all=True,
                        append_images=res[1:], duration=2000, loop=0,
                        disposal=2)
            collection.thumb_created = datetime.datetime.now().timestamp()
        await collection.save(db)
        return True

    @classmethod
    async def __search_in_cache(cls, uuid, original_desc, db):
        len_original = len(original_desc)
        index_params = dict(algorithm=0, trees=5)
        search_params = dict()
        uuids = {}
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        # for uuid2, desc_2 in cls.DESCRIPTIONS.items():
        for key in await db.r.keys('matrix:*'):
            uuid2 = key.replace('matrix:', '')
            if uuid2 == uuid:
                continue
            len_keys = int(await db.r.hget(key, 'number_keys'))
            if len_keys > 10 * len_original or len_keys < len_original / 10:
                continue
            desc2 = await db.r.execute_command('HGET', key, 'descriptions',
                                               NEVER_DECODE=True)
            desc_2 = pickle.loads(desc2)
            matches = flann.knnMatch(original_desc, desc_2, k=2)
            len_desc2 = len(desc_2)
            del desc_2
            good_points = []
            for m, n in matches:
                if m.distance < 0.6 * n.distance:
                    good_points.append(m)
            len_key_points = min(len_original, len_desc2)
            percent = round(len(good_points) / len_key_points, 4) * 100
            if percent > 40:
                uuids[uuid2] = percent
        return uuids

    @staticmethod
    def __serialize_key_points(key_points):
        keypoints_data = []
        for keypoint in key_points:
            data = {
                'pt': keypoint.pt,
                'size': keypoint.size,
                'angle': keypoint.angle,
                'response': keypoint.response,
                'octave': keypoint.octave,
                'class_id': keypoint.class_id
            }
            keypoints_data.append(data)
        return keypoints_data

    @classmethod
    # @profile
    async def find_same_images(cls, image, db: RedisManager, **kwargs):
        try:
            uuid = image.uuid.split(':').pop()
            sift = cv2.SIFT_create()
            if image.content_type.endswith('gif'):
                gif_reader = imageio.get_reader(image.full_thumb_image_path)
                max_points = (-1, 0)
                counter = 0
                for frame in gif_reader:
                    # We try to find the frame with the most keys
                    counter += 1
                    key_points = sift.detectAndCompute(frame, None)
                    if len(key_points) > max_points[1]:
                        max_points = (counter, len(key_points))
                img = cv2.cvtColor(gif_reader.get_data(max_points[0]),
                                   cv2.COLOR_BGR2GRAY)
                key_points, desc = sift.detectAndCompute(img, None)
                del gif_reader
            else:
                img = cv2.imread(image.full_thumb_image_path,
                                 cv2.IMREAD_GRAYSCALE)
                key_points, desc = sift.detectAndCompute(img, None)
                del img
            len_keys = len(key_points)
            if len_keys < 50:
                logger.warning(
                    f'TheImage {image.uuid} has got less keys ({len_keys}).')
                return False
            if len_keys != len(desc):
                logger.error(
                    f'Image {image.uuid} has got different number keys '
                    f'({len_keys}) and desc ({len(desc)})')
            similar_images_uuids = await cls.__search_in_cache(uuid, desc, db)
            # cls.DESCRIPTIONS[uuid] = desc
            if similar_images_uuids:
                logger.info(
                    f'The Image {image.uuid} has got good '
                    f'match with {similar_images_uuids}.')
            # else:
            #     print(f'The Image {image.uuid} has got no good match')
            await db.r.hset(f'matrix:{uuid}', mapping={
                'number_keys': len_keys,
                'key_points': pickle.dumps(
                    cls.__serialize_key_points(key_points)),
                'descriptions': pickle.dumps(desc),
                'similar_images_uuids': json.dumps(similar_images_uuids)
            })
            await asyncio.sleep(.1)
            return True
        except Exception as ex:
            logger.error(f'The problem with image {image.uuid}. {ex}',
                         exc_info=ex)
            return False
