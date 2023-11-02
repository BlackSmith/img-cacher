import math

from modules.image import Image


class ImageActionException(Exception): pass     # noqa


class Action:
    TYPE = None

    @classmethod
    def test(cls, image: Image) -> bool:
        return image.content_type.startswith(cls.TYPE)

    @classmethod
    def calculation_size(cls, c_width, c_height, width, height):
        if c_height >= c_width and height:
            width = math.ceil(c_width / (c_height / height))
        elif c_width >= c_height and width:
            height = math.ceil(c_height / (c_width / width))
        else:
            raise ImageActionException(
                'Resizing requires width and height parameter.')
        return width, height
