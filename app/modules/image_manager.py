from loggate import get_logger

from libs.redis_manager import redis_subscribe, RedisManager
from libs.socket_manager import socket_command, SocketManager
from libs.helper import login_required
from modules.collection import Collection
from modules.image import Image
from modules.image_request_parser import ImageRequest

logger = get_logger('ImageManager')


class ImageManager:
    @socket_command('get_collection_images')
    @staticmethod
    async def get_collection_images(payload, db, **kwargs):
        collection_name = payload.get('collection')
        if not collection_name:
            collection_name = '@'
        # TODO: check enabled collection
        collection = await Collection.get(collection_name, db)
        res = {key: val for key, val in collection.__dict__.items() if
               val and not key.startswith('_')}
        res['members'] = await collection.get_members(db, offset=payload.get(
            'offset', 0), num=payload.get('num', 10000))
        return res

    @socket_command('get_image_alternates')
    @staticmethod
    async def get_image_alternates(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(**params)
        image = await Image.get(irp, db=db)
        result = []
        if image:
            result.append(image.data)
            for ai in await image.get_all_alternates(db):
                result.append(ai.data)
        # data['count'] = len(data['items'])
        return {'data': result}

    @socket_command('add_image_link')
    @staticmethod
    async def get_image_alternates(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(uuid=params.get('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        uuid = params.get('url', '')
        if uuid.startswith('http'):
            uuid = ImageRequest.make_uuid(uuid)
        if uuid not in image.original_uuid:
            image.original_uuid = f'{uuid};{image.original_uuid}'
            await image.save(db)
        return {'status': 'ok'}

    @socket_command('get_collection_list')
    @staticmethod
    async def get_collection_list(payload, db, **kwargs):
        collections = await Collection.get_collections(db=db)
        return {'data': collections}

    @socket_command('update_image')
    @login_required
    @staticmethod
    async def update_image(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(uuid=params.pop('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        for key, val in params.items():
            logger.info(
                f"Update image attribute {key}='{val}' (uuid: {irp.uuid})")
            setattr(image, key, val)
        await image.save(db)
        return {'status': 'ok'}

    @socket_command('delete_image')
    @login_required
    @staticmethod
    async def delete_image(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(uuid=params.pop('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        logger.info(f"Delete image (uuid: {irp.uuid})")
        await image.delete(db)
        return {'status': 'ok'}

    @socket_command('set_image_collection')
    @login_required
    @staticmethod
    async def set_image_collection(payload, db, **kwargs):
        params = payload.get('params')
        collection_name = params.get('collection')
        for uuid in params.pop('uuid', []):
            uuids = uuid.split(':', 1)
            irp = ImageRequest(uuid=uuids[0])
            image = await Image.get(irp, db=db)
            if not image:
                return {'status': 'ng', 'msg': 'Image not found.'}
            if image.collection == collection_name:
                return {'status': 'ng', 'msg': 'The same collection.'}
            collection = await Collection.get(collection_name, db)
            logger.info(
                f"Move image (uuid: {irp.uuid}) "
                f"to collection '{collection_name}'")
            await image.set_collection(db, collection)
        return {'status': 'ok'}

    @socket_command('set_main_image')
    @login_required
    @staticmethod
    async def set_main_image(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(uuid=params.pop('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        logger.info(f"Set main image (uuid: {irp.full_uuid})")
        await image.set_as_main(db)
        return {'status': 'ok'}

    @socket_command('join_images')
    @login_required
    @staticmethod
    async def join_images(payload, db, **kwargs):
        params = payload.get('params')
        uuids = params.get('uuids', [])
        if len(uuids) < 2:
            return {'status': 'ng', 'msg': 'Required minimum two images.'}
        main_image = await Image.get(ImageRequest(uuid=uuids.pop(0)), db=db)
        if not main_image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        logger.info(f"Join images (uuids: {uuids}) to image {main_image.uuid}")
        for uuid in uuids:
            image = await Image.get(ImageRequest(uuid=uuid), db=db)
            await image.set_as_alternation_of(main_image, db=db)
            if alternates := await image.get_all_alternates():
                for a_image in alternates:
                    await a_image.set_as_alternation_of(main_image, db=db)
        await main_image.move_to_own_subfolder(db)
        return {'status': 'ok'}

    @socket_command('redownload_image')
    @login_required
    @staticmethod
    async def redownload_image(payload, db, **kwargs):
        params = payload.get('params')
        irp = ImageRequest(uuid=params.pop('uuid'))
        image = await Image.get(irp, db=db)
        if not image:
            return {'status': 'ng', 'msg': 'Image not found.'}
        if await image.redownload(url=params.get('url')):
            await image.save(db)
            await image.make_thumb(db, True)
        return {'status': 'ok'}

    @redis_subscribe('__key*__:images:*')
    @staticmethod
    async def image_changed(channel: str, action: str, db: RedisManager,
                            socket: SocketManager, **kwargs):
        logger.info(f'Redis change {channel} : {action}')
        irp = ImageRequest(redis_channel=channel)
        if irp.uuid:
            if action == 'del':
                await socket.publish({'action': 'image.delete_handler',
                                      'data': {'uuid': irp.full_uuid}})
                return
            image = await Image.get(irp, db)
            if not image:
                logger.error(f'The image {irp.full_uuid} does not exist.')
            else:
                logger.info(
                    f"Publish update for image "
                    f"{irp.full_uuid} ({image.filename}).")
                if action == 'hset':
                    await socket.publish({'action': 'image.update',
                                          'data': image.data})
                if action == 'rename_to':
                    await socket.publish({
                        'action': 'image.move_handler',
                        'data': {
                            'from': ImageRequest(
                                redis_channel=kwargs.get('rename_from')
                            ).full_uuid,
                            'to': irp.full_uuid
                        }})
