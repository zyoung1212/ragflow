#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import json
import uuid
import os
import threading

import valkey as redis
from rag import settings
from rag.utils import singleton
from valkey.lock import Lock
import trio

class RedisMsg:
    def __init__(self, consumer, queue_name, group_name, msg_id, message):
        self.__consumer = consumer
        self.__queue_name = queue_name
        self.__group_name = group_name
        self.__msg_id = msg_id
        self.__message = json.loads(message["message"])

    def ack(self):
        try:
            self.__consumer.xack(self.__queue_name, self.__group_name, self.__msg_id)
            return True
        except Exception as e:
            logging.warning("[EXCEPTION]ack" + str(self.__queue_name) + "||" + str(e))
        return False

    def get_message(self):
        return self.__message

    def get_msg_id(self):
        return self.__msg_id


class RedisDB:
    _instance = None
    _lock = threading.Lock()
    
    lua_delete_if_equal = None
    LUA_DELETE_IF_EQUAL_SCRIPT = """
        local current_value = redis.call('get', KEYS[1])
        if current_value and current_value == ARGV[1] then
            redis.call('del', KEYS[1])
            return 1
        end
        return 0
    """

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RedisDB, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.REDIS = None
        self.config = settings.REDIS
        self._local = threading.local()
        self.__open__()
        self._initialized = True

    def register_scripts(self) -> None:
        cls = self.__class__
        client = self.get_connection()
        if client:
            cls.lua_delete_if_equal = client.register_script(cls.LUA_DELETE_IF_EQUAL_SCRIPT)

    def get_connection(self):
        """获取线程本地的Redis连接"""
        if not hasattr(self._local, 'redis_client') or self._local.redis_client is None:
            try:
                self._local.redis_client = redis.StrictRedis(
                    host=self.config["host"].split(":")[0],
                    port=int(self.config.get("host", ":6379").split(":")[1]),
                    db=int(self.config.get("db", 1)),
                    password=self.config.get("password"),
                    decode_responses=True,
                    # 添加连接池配置
                    connection_pool=redis.ConnectionPool(
                        host=self.config["host"].split(":")[0],
                        port=int(self.config.get("host", ":6379").split(":")[1]),
                        db=int(self.config.get("db", 1)),
                        password=self.config.get("password"),
                        decode_responses=True,
                        max_connections=20,  # 每个进程最大连接数
                        retry_on_timeout=True,
                        socket_keepalive=True,
                        socket_keepalive_options={},
                        health_check_interval=30,
                    )
                )
                # 为每个连接注册脚本
                if not self.lua_delete_if_equal:
                    self.lua_delete_if_equal = self._local.redis_client.register_script(self.LUA_DELETE_IF_EQUAL_SCRIPT)
            except Exception as e:
                logging.warning(f"Redis can't be connected: {e}")
                self._local.redis_client = None
        
        return self._local.redis_client

    def __open__(self):
        # 主连接仅用于兼容性，实际使用get_connection()
        try:
            self.REDIS = redis.StrictRedis(
                host=self.config["host"].split(":")[0],
                port=int(self.config.get("host", ":6379").split(":")[1]),
                db=int(self.config.get("db", 1)),
                password=self.config.get("password"),
                decode_responses=True,
            )
            self.register_scripts()
        except Exception as e:
            logging.warning(f"Redis can't be connected: {e}")
        return self.REDIS

    def health(self):
        client = self.get_connection()
        if not client:
            return False
        try:
            client.ping()
            a, b = "xx", "yy"
            client.set(a, b, 3)
            return client.get(a) == b
        except Exception as e:
            logging.warning(f"Redis health check failed: {e}")
            return False

    def is_alive(self):
        return self.get_connection() is not None

    def exist(self, k):
        client = self.get_connection()
        if not client:
            return False
        try:
            return client.exists(k)
        except Exception as e:
            logging.warning("RedisDB.exist " + str(k) + " got exception: " + str(e))
            # 重置连接
            self._local.redis_client = None
            return False

    def get(self, k):
        client = self.get_connection()
        if not client:
            return None
        try:
            return client.get(k)
        except Exception as e:
            logging.warning("RedisDB.get " + str(k) + " got exception: " + str(e))
            # 重置连接
            self._local.redis_client = None
            return None

    # 其他方法类似地修改，都使用get_connection()而不是self.REDIS
    def set_obj(self, k, obj, exp=3600):
        try:
            self.REDIS.set(k, json.dumps(obj, ensure_ascii=False), exp)
            return True
        except Exception as e:
            logging.warning("RedisDB.set_obj " + str(k) + " got exception: " + str(e))
            self.__open__()
        return False

    def set(self, k, v, exp=3600):
        try:
            self.REDIS.set(k, v, exp)
            return True
        except Exception as e:
            logging.warning("RedisDB.set " + str(k) + " got exception: " + str(e))
            self.__open__()
        return False

    def sadd(self, key: str, member: str):
        try:
            self.REDIS.sadd(key, member)
            return True
        except Exception as e:
            logging.warning("RedisDB.sadd " + str(key) + " got exception: " + str(e))
            self.__open__()
        return False

    def srem(self, key: str, member: str):
        try:
            self.REDIS.srem(key, member)
            return True
        except Exception as e:
            logging.warning("RedisDB.srem " + str(key) + " got exception: " + str(e))
            self.__open__()
        return False

    def smembers(self, key: str):
        try:
            res = self.REDIS.smembers(key)
            return res
        except Exception as e:
            logging.warning(
                "RedisDB.smembers " + str(key) + " got exception: " + str(e)
            )
            self.__open__()
        return None

    def zadd(self, key: str, member: str, score: float):
        try:
            self.REDIS.zadd(key, {member: score})
            return True
        except Exception as e:
            logging.warning("RedisDB.zadd " + str(key) + " got exception: " + str(e))
            self.__open__()
        return False

    def zcount(self, key: str, min: float, max: float):
        try:
            res = self.REDIS.zcount(key, min, max)
            return res
        except Exception as e:
            logging.warning("RedisDB.zcount " + str(key) + " got exception: " + str(e))
            self.__open__()
        return 0

    def zpopmin(self, key: str, count: int):
        try:
            res = self.REDIS.zpopmin(key, count)
            return res
        except Exception as e:
            logging.warning("RedisDB.zpopmin " + str(key) + " got exception: " + str(e))
            self.__open__()
        return None

    def zrangebyscore(self, key: str, min: float, max: float):
        try:
            res = self.REDIS.zrangebyscore(key, min, max)
            return res
        except Exception as e:
            logging.warning(
                "RedisDB.zrangebyscore " + str(key) + " got exception: " + str(e)
            )
            self.__open__()
        return None

    def transaction(self, key, value, exp=3600):
        try:
            pipeline = self.REDIS.pipeline(transaction=True)
            pipeline.set(key, value, exp, nx=True)
            pipeline.execute()
            return True
        except Exception as e:
            logging.warning(
                "RedisDB.transaction " + str(key) + " got exception: " + str(e)
            )
            self.__open__()
        return False

    def queue_product(self, queue, message) -> bool:
        for _ in range(3):
            try:
                payload = {"message": json.dumps(message)}
                self.REDIS.xadd(queue, payload)
                return True
            except Exception as e:
                logging.exception(
                    "RedisDB.queue_product " + str(queue) + " got exception: " + str(e)
                )
        return False

    def queue_consumer(self, queue_name, group_name, consumer_name, msg_id=b">") -> RedisMsg:
        """https://redis.io/docs/latest/commands/xreadgroup/"""
        try:
            group_info = self.REDIS.xinfo_groups(queue_name)
            if not any(gi["name"] == group_name for gi in group_info):
                self.REDIS.xgroup_create(queue_name, group_name, id="0", mkstream=True)
            args = {
                "groupname": group_name,
                "consumername": consumer_name,
                "count": 1,
                "block": 5,
                "streams": {queue_name: msg_id},
            }
            messages = self.REDIS.xreadgroup(**args)
            if not messages:
                return None
            stream, element_list = messages[0]
            if not element_list:
                return None
            msg_id, payload = element_list[0]
            res = RedisMsg(self.REDIS, queue_name, group_name, msg_id, payload)
            return res
        except Exception as e:
            if str(e) == 'no such key':
                pass
            else:
                logging.exception(
                    "RedisDB.queue_consumer "
                    + str(queue_name)
                    + " got exception: "
                    + str(e)
                )
        return None

    def get_unacked_iterator(self, queue_names: list[str], group_name, consumer_name):
        try:
            for queue_name in queue_names:
                try:
                    group_info = self.REDIS.xinfo_groups(queue_name)
                except Exception as e:
                    if str(e) == 'no such key':
                        logging.warning(f"RedisDB.get_unacked_iterator queue {queue_name} doesn't exist")
                        continue
                if not any(gi["name"] == group_name for gi in group_info):
                    logging.warning(f"RedisDB.get_unacked_iterator queue {queue_name} group {group_name} doesn't exist")
                    continue
                current_min = 0
                while True:
                    payload = self.queue_consumer(queue_name, group_name, consumer_name, current_min)
                    if not payload:
                        break
                    current_min = payload.get_msg_id()
                    logging.info(f"RedisDB.get_unacked_iterator {queue_name} {consumer_name} {current_min}")
                    yield payload
        except Exception:
            logging.exception(
                "RedisDB.get_unacked_iterator got exception: "
            )
            self.__open__()

    def get_pending_msg(self, queue, group_name):
        try:
            messages = self.REDIS.xpending_range(queue, group_name, '-', '+', 10)
            return messages
        except Exception as e:
            if 'No such key' not in (str(e) or ''):
                logging.warning(
                    "RedisDB.get_pending_msg " + str(queue) + " got exception: " + str(e)
                )
        return []

    def requeue_msg(self, queue: str, group_name: str, msg_id: str):
        try:
            messages = self.REDIS.xrange(queue, msg_id, msg_id)
            if messages:
                self.REDIS.xadd(queue, messages[0][1])
                self.REDIS.xack(queue, group_name, msg_id)
        except Exception as e:
            logging.warning(
                "RedisDB.get_pending_msg " + str(queue) + " got exception: " + str(e)
            )

    def queue_info(self, queue, group_name) -> dict | None:
        try:
            groups = self.REDIS.xinfo_groups(queue)
            for group in groups:
                if group["name"] == group_name:
                    return group
        except Exception as e:
            logging.warning(
                "RedisDB.queue_info " + str(queue) + " got exception: " + str(e)
            )
        return None

    def delete_if_equal(self, key: str, expected_value: str) -> bool:
        """原子性删除操作"""
        client = self.get_connection()
        if not client or not self.lua_delete_if_equal:
            return False
        try:
            return bool(self.lua_delete_if_equal(keys=[key], args=[expected_value], client=client))
        except Exception as e:
            logging.warning(f"RedisDB.delete_if_equal {key} got exception: {e}")
            self._local.redis_client = None
            return False


# 移除@singleton装饰器，使用新的单例实现
REDIS_CONN = RedisDB()


class RedisDistributedLock:
    def __init__(self, lock_key, lock_value=None, timeout=10, blocking_timeout=1):
        self.lock_key = lock_key
        if lock_value:
            self.lock_value = lock_value
        else:
            self.lock_value = str(uuid.uuid4())
        self.timeout = timeout
        # 使用线程本地连接
        redis_client = REDIS_CONN.get_connection()
        if redis_client:
            self.lock = Lock(redis_client, lock_key, timeout=timeout, blocking_timeout=blocking_timeout)
        else:
            self.lock = None

    def acquire(self):
        if not self.lock:
            return False
        REDIS_CONN.delete_if_equal(self.lock_key, self.lock_value)
        try:
            return self.lock.acquire(token=self.lock_value)
        except Exception as e:
            logging.warning(f"Lock acquire failed: {e}")
            return False

    async def spin_acquire(self):
        if not self.lock:
            return False
        REDIS_CONN.delete_if_equal(self.lock_key, self.lock_value)
        while True:
            try:
                if self.lock.acquire(token=self.lock_value):
                    break
            except Exception as e:
                logging.warning(f"Lock spin_acquire failed: {e}")
            await trio.sleep(10)

    def release(self):
        REDIS_CONN.delete_if_equal(self.lock_key, self.lock_value)
