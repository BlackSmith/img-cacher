import datetime
import os
import re
import secrets
import string

import bcrypt
from jose import jwt
from loggate import get_logger

from config import get_config
from libs.redis_manager import RedisManager
from libs.socket_manager import socket_command

JWT_SECRET = get_config('JWT_SECRET')
JWT_ALGORITHM = get_config('JWT_ALGORITHM')
JWT_EXPIRATION = get_config('JWT_EXPIRATION', wrapper=int)
logger = get_logger('UserManager')


class UserManager:

    @socket_command('user_login')
    @staticmethod
    async def user_login(payload, db, socket):
        params = payload.get('params')
        username = params.get('username')
        if username and ':' not in username and \
                (account_hash := await db.r.hget(f'users:{username}', 'hash')):
            if bcrypt.checkpw(params.get('password').encode(),
                              account_hash.encode()):
                data = await db.r.hgetall(f'users:{username}')
                del data['hash']
                data['username'] = username
                if params.get('remember_me'):
                    data['remember_me'] = True
                    data['exp'] = datetime.datetime.utcnow() \
                        + datetime.timedelta(days=JWT_EXPIRATION)
                socket.user_data = data
                access_token = jwt.encode(data, JWT_SECRET,
                                          algorithm=JWT_ALGORITHM)
                res = {'status': 'ok', 'access_token': access_token}
                logger.info(f'Login user {username}')
                return res
        return {'status': 'ng'}

    @socket_command('automatic_login')
    @staticmethod
    async def automatic_login(payload, db, socket):
        try:
            data = jwt.decode(payload.get('access_token'), JWT_SECRET,
                              algorithms=[JWT_ALGORITHM])
            socket.user_data = data
            logger.info(f"Automatic login user '{data['username']}'")
            return {'status': 'ok'}
        except Exception as ex:
            logger.error(f"Automatic login failed. {ex}")
            return {'status': 'ng'}

    @staticmethod
    async def create_account(username: str, password: str, db: RedisManager):
        if account_hash := await db.r.hget(f'users:{username}', 'hash'):
            if not bcrypt.checkpw(password.encode(), account_hash.encode()):
                await db.r.hset(f'users:{username}', 'hash',
                                bcrypt.hashpw(password.encode(),
                                              bcrypt.gensalt()))
                logger.info(
                    f"The user account '{username}' has got "
                    f"a new password '{password}'.")
            return
        await db.r.hset(f'users:{username}', mapping={
            'hash': bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
            'created': int(datetime.datetime.now().timestamp())
        })
        logger.info(
            f"The new user account '{username}' was "
            f"created with password '{password}'.")

    @classmethod
    async def create_accounts_by_env(cls, db):
        users = {}
        for name, value in os.environ.items():
            if match := re.match(r'^ICACHER_USERNAME(?P<num>\d*)', name):
                ix = match.group('num')
                if passwd := os.getenv(f'ICACHER_PASSWORD{ix}', None):
                    users[value] = passwd
        if not users and not await db.r.keys('users:*'):
            characters = string.ascii_letters + string.digits
            users['user'] = ''.join(
                secrets.choice(characters) for _ in range(12)
            )
        for username, passwd in users.items():
            await cls.create_account(username, passwd, db)
