import time
import json
import fnmatch
import threading
from .errors import BucketError
from redis import StrictRedis, exceptions


class LocalBucket(object):
    """进程内存储，重启后数据丢失"""
    _lock = None
    _instances = {}

    def __init__(self):
        self._db = {}
        if LocalBucket._lock is None:
            LocalBucket._lock = threading.Lock()

    @classmethod
    def instance(cls, name):
        """获取单例"""
        var = LocalBucket._instances.get(name, None)
        if var:
            return var
        var = LocalBucket()
        LocalBucket._instances[name] = var
        return var

    @classmethod
    def purge(cls):
        """清理由instance创建的所有实例的过期key，返回被清理的数量"""
        count = 0
        for instance in cls._instances.values():
            count += instance._purge()
        return count

    def _purge(self):
        """清理实例中过期的key，返回被清理的数量"""
        keys = []
        for key, (_, expire_at) in self._db.items():
            if expire_at is not None and expire_at <= time.time():
                keys.append(key)
        for key in keys:
            del self._db[key]
        return len(keys)

    def set(self, key, value, ttl=None):
        """为key设置value，ttl秒后失效"""
        item = self._db.get(key, None)
        if item is None or ttl is not None:
            # 更改value和ttl
            if ttl is None:
                expire_at = None
            else:
                expire_at = time.time() + ttl
            self._db[key] = [value, expire_at]
        else:
            # 只更改ttl
            self._db[key][0] = value

    def delete(self, *keys) -> int:
        """删除一个或多个key，返回被删除的数量"""
        count = 0
        for key in keys:
            item = self._db.get(key, None)
            # 忽略不存在的key
            if item is None:
                continue
            expire_at = item[1]
            if expire_at is None or expire_at > time.time():
                del self._db[key]
                count += 1
            else:  # 键已过期，不累加计数器
                del self._db[key]
        return count

    def get(self, key) -> object:
        """返回key的value，当key不存在时返回None"""
        item = self._db.get(key, None)
        if item is None:
            return None
        value, expire_at = item
        if expire_at is None:
            return value
        elif expire_at > time.time():
            return value
        else:  # 键已过期
            del self._db[key]
            return None

    def getset(self, key, value) -> object:
        """为给定key设置新value，返回旧value"""
        old_value = self.get(key)
        self.set(key, value)
        return old_value

    def keys(self, pattern='*') -> list:
        """
        返回满足pattern的所有键
        pattern支持通配符：?、*、[]
        """
        expired_keys = []
        valid_keys = []
        n = time.time()
        for key, (_, expire_at) in self._db.items():
            if expire_at is not None and expire_at <= n:
                expired_keys.append(key)
            else:
                if fnmatch.fnmatch(key, pattern):
                    valid_keys.append(key)
        for key in expired_keys:
            del self._db[key]
        return valid_keys

    def expire(self, key, ttl) -> bool:
        """为给定key设置生存时间，ttl秒后被自动删除"""
        item = self._db.get(key, None)
        if item is None:
            return False
        _, expire_at = item
        if expire_at is None or expire_at >= time.time():
            self._db[key][1] = ttl + time.time()
            return True
        else:  # 键已过期
            del self._db[key]
            return False

    def ttl(self, key) -> int:
        """
        返回给定key的剩余生存时间
        Returns:
            当key不存在时，返回-2;
            当key存在但没有设置剩余生存时间时，返回-1;
            否则，返回key的剩余生存时间
        """
        item = self._db.get(key, None)
        if item is None:
            return -2
        value, expire_at = item
        if expire_at is None:
            return -1
        elif expire_at > time.time():
            return expire_at - time.time()
        else:  # 键已过期
            del self._db[key]
            return -2

    def incr(self, key, amount=1) -> int:
        """
        将给定key的值加上amount，返回incr后的值
        若key不存在，key被先初始化为0，再incr
        若value非int型，抛出异常
        """
        with LocalBucket._lock:
            old_value = self.get(key)
            if old_value is None:
                self.set(key, 0, None)
                old_value = 0
            elif not isinstance(old_value, int):
                raise BucketError("incr应作用于int型的值")
            new_value = old_value + amount
            self.set(key, new_value)
            return new_value


class ShareBucket(object):
    """共享存储，利用redis存储，不易失"""
    prefix = "bucket"

    def __init__(self, db: StrictRedis, name):
        self._db = db
        self.name = name
        self.key_prefix = f"{self.prefix}:{name}"

    def set(self, key, value, ttl=None):
        """为key设置value，ttl秒后失效"""
        self._db.set(f"{self.key_prefix}:{key}", json.dumps(value), ex=ttl)

    def delete(self, *keys) -> int:
        """删除一个或多个key，返回被删除的数量"""
        return self._db.delete(*[f"{self.key_prefix}:{k}" for k in keys])

    def get(self, key) -> object:
        """返回key的value，当key不存在时返回None"""
        res = self._db.get(f"{self.key_prefix}:{key}")
        if res:
            return json.loads(res)
        else:
            return res

    def getset(self, key, value) -> object:
        """为给定key设置新value，返回旧value"""
        res = self._db.getset(f"{self.key_prefix}:{key}", value)
        if res:
            return json.loads(res)
        else:
            return res

    def keys(self, pattern='*') -> list:
        """
        返回满足pattern的所有键
        pattern支持通配符：?、*、[]
        """
        p = len(f"{self.key_prefix}:")
        res = self._db.keys(f"{self.key_prefix}:{pattern}")
        return [r.decode()[p:] for r in res]

    def expire(self, key, ttl) -> bool:
        """为给定key设置生存时间，ttl秒后被自动删除"""
        return self._db.expire(f"{self.key_prefix}:{key}", ttl)

    def ttl(self, key) -> int:
        """
        返回给定key的剩余生存时间
        Returns:
            当key不存在时，返回-2;
            当key存在但没有设置剩余生存时间时，返回-1;
            否则，返回key的剩余生存时间
        """
        return self._db.ttl(f"{self.key_prefix}:{key}")

    def incr(self, key, amount=1) -> int:
        """
        将给定key的值加上amount，返回incr后的值
        若key不存在，key被先初始化为0，再incr
        若value非int型，抛出异常
        """
        try:
            return self._db.incr(f"{self.key_prefix}:{key}", amount)
        except exceptions.ResponseError as e:
            if e.args[0] == 'value is not an integer or out of range':
                raise BucketError("incr应作用于int型的值")

    def lpush(self, key, *values) -> int:
        """
        将一个或多个值value插入到列表key的表头
        返回执行LPUSH命令后，列表的长度。
        """
        return self._db.lpush(f"{self.key_prefix}:{key}", *values)

    def lrange(self, key, start, end) -> list:
        """
        返回列表 key 中指定区间内的元素，区间以偏移量 start 和 stop 指定。
        包含指定区间内的元素的list
        """
        return self._db.lrange(f"{self.key_prefix}:{key}", start, end)

    def lock(self, key, timeout, **kwargs):
        """分布式锁"""
        return self._db.lock(f"{self.key_prefix}:{key}", timeout, **kwargs)
