"""Scheduler SDK"""
import json
import time
import copy
import random
import logging
from .errors import *
from redis import StrictRedis
from . import utils, tasks, buckets

key_spiders = "spiders"  # set
logger = logging.getLogger("scheduler")


class Spider(object):
    prefix = "spider"
    _caches = {}
    _timeout = 10
    status = {
        0: '已完成',
        10: '就绪',
        20: '等待代理',  # 暂未实现
        21: '等待时间',  # 暂未实现
        -1: '异常关闭',
        -2: '主动关闭'
    }

    def __init__(self, db: StrictRedis, name):
        self.name = name  # 爬虫名
        self._db = db
        self.key = f"{self.prefix}:{self.name}"  # 主键
        self.fields = {  # 爬虫所有字段及可缓存时间
            "interval": 300,
            "timeout": 300,
            "precision": 10000,
            "args": 300,
            "last_pop_time": 1,
            "status": 1,
            "version": 1,
            "proxies": 1,
            "last_heartbeat_time": 6
        }

    def exists(self):
        """爬虫是否存在"""
        return self._db.exists(self.key)

    def upsert(self, seeders, interval, timeout, precision, args, proxies, version):
        """
        新建爬虫或覆盖同名爬虫的配置（仅当版本号更大时）
        Args:
            seeders: 种子页面
            interval: 最小调度间隔（误差由pop频率决定）
            timeout: 任务超时时间
            precision: 布隆过滤器精度
            args: 自定义爬虫参数
            proxies: 使用代理运行
            version: 配置版本，等于目录的sha1值
        Returns:
            T/F: 是否更新了配置
        """
        # 当前版本比数据库的还小就不更新了
        _version = self._get_field("version")
        if _version is not None and version <= _version:
            return False
        # 忽略更新precision字段
        _precision = self._get_field("precision")
        if _precision is not None:
            precision = _precision
        # 爬虫配置
        values = {
            "interval": interval,
            "timeout": timeout,
            "precision": precision,
            "args": args,
            "last_pop_time": 0,
            "status": 10,  # 0:已完成，10:就绪，20:等待代理，21:等待时间，-1:异常关闭，-2:主动关闭
            "version": version,
            "proxies": proxies,  # 代理配置
            "last_heartbeat_time": 0,  # 最后一次尝试申请任务的时间
        }
        self._db.hmset(self.key, {k: json.dumps(v) for k, v in values.items()})
        self._db.sadd(key_spiders, self.name)
        # 将种子URL入队
        queues = Queue(self._db, self.name)
        queues.add(seeders, 0)
        return True

    def _get_field(self, field):
        """从数据库中查询并返回爬虫的配置项"""
        if field not in self.fields:
            raise SchedulerError(f"没有此配置项'{field}'")

        res = self._db.hget(self.key, field)
        if res is None:
            return None
        else:
            return json.loads(res)

    def get_field(self, field):
        """依此从缓存、数据库中查询并返回爬虫的配置项"""
        if field not in self.fields:
            raise SchedulerError(f"没有此配置项'{field}'")

        timeout = self.fields[field]
        # 先尝试从缓存取值
        cache_key = f"{self.name}:{field}"
        var, start = Spider._caches.get(cache_key, (None, 0))
        if start + timeout < time.time():
            # 缓存过期或无缓存
            var = self._get_field(field)
            if timeout > 0:
                Spider._caches[cache_key] = (var, time.time())
        return var

    def set_field(self, field, value):
        """覆写爬虫的配置项"""
        if field not in self.fields:
            raise SchedulerError(f"没有此配置项'{field}'")
        if field == 'precision':
            raise SchedulerError(f"配置项被锁定'{field}'")

        self._db.hset(self.key, field, json.dumps(value))
        # 设置缓存
        cache_key = f"{self.name}:{field}"
        timeout = self.fields[field]
        if timeout > 0:
            Spider._caches[cache_key] = (value, time.time())

    @classmethod
    def names(cls, db: StrictRedis):
        """返回所有爬虫名称的列表"""
        return [r.decode() for r in db.smembers(key_spiders)]

    def clear_queue(self):
        """清除该爬虫在队列中留存的数据"""
        keys = []
        keys += self._db.keys(f"{Spider.prefix}:{self.name}")
        keys += self._db.keys(f"{Queue.prefix}:{self.name}:*")
        keys += self._db.keys(f"{buckets.ShareBucket.prefix}:{self.name}:*")
        keys += self._db.keys(f"{tasks.Tracking.prefix}:{self.name}:*")
        return self._db.delete(*keys) if keys else 0

    def clear_proxy(self):
        """清空该爬虫的代理池"""
        count = self._db.delete(f"proxy:addresses:{self.name}")
        count += self._db.srem(key_spiders, self.name)
        return count


class Queue(object):
    prefix = "queue"

    def __init__(self, db: StrictRedis, name):
        self.name = name  # 爬虫名
        self._db = db
        self._spider = Spider(db, name)
        # 等待队列（list），5个优先级分别用5个list实现，左进右出
        # [[url0, url1], [url0, url1], [url0, url1]]
        self.key_waiting = [f"{self.prefix}:{self.name}:waiting:{i}" for i in range(5)]
        # 进行队列（hash），field=url, value=timestamp
        self.key_processing = f"{self.prefix}:{self.name}:processing"
        # 异常标签（set）
        self.key_tags = f"{self.prefix}:{self.name}:tags"
        # 异常队列（list）
        self.prefix_error = f"{self.prefix}:{self.name}:errors"  # :{tag}
        # 队列过滤器（set），过滤waiting、processing、errors中的URl
        self.key_filter_queue = f"{self.prefix}:{self.name}:filter:queue"
        # 结果过滤器（string or set），过滤已抓取完成的URL
        # 结果过滤器有两种实现：set、bloom，通过爬虫配置项'queue.filter'选择适合的实现
        self.key_filter_bloom_count = f"{self.prefix}:{self.name}:filter:bloom:count"

    def exists(self, url):
        """
        URL是否存在
        Returns:
            0: 不存在
            1: 存在于bloom中
            2: 存在于queue中
        """
        # 在results中找
        sha = utils.RedisScripts.sha1('bloom_check')
        if self._db.evalsha(sha, 1, self.name, url):
            return 1
        # 在queue中找
        if self._db.sismember(self.key_filter_queue, url):
            return 2
        else:
            return 0

    def insert(self, url, priority):
        """忽略布隆检查，将URL插入至队列中"""
        self._db.lpush(self.key_waiting[priority], url)
        self._db.sadd(self.key_filter_queue, url)
        self._db.hdel(self.key_processing, url)

    def add(self, urls, priority):
        """
        URL批量入队
        当URL相同，但priority不同时，也视为重复
        Returns: 经排重后添加至队列的数量
        """
        if not isinstance(priority, int):
            raise SchedulerError("priority应为int型")
        if priority < 0 or priority >= len(self.key_waiting):
            raise SchedulerError(f"priority可选范围为:{list(range(len(self.key_waiting)))}")

        urls = list(set(urls))
        sha = utils.RedisScripts.sha1('url_add')
        return self._db.evalsha(sha, 2, self.name, priority, *urls)

    @classmethod
    def pop(cls, db: StrictRedis, names):
        """
        从指定爬虫中弹出一条最合适的URL
        Returns: (url, name)
            当所有队列为空时，url == name == None
        """
        # 随机挑选爬虫
        names = copy.deepcopy(names)
        random.shuffle(names)

        sha = utils.RedisScripts.sha1('url_pop')
        url, name, address = db.evalsha(sha, 1, time.time(), *names)
        if url and name:
            return [url.decode(), name.decode(), address.decode() if address else None]
        else:
            return [None, None, None]

    @classmethod
    def purge(cls, db: StrictRedis):
        """
        清理processing中过期的URL，返回被清理数量
        被清理的URL，将被打上"timeout"标签，移入error队列
        """
        count = 0
        for name in Spider.names(db):
            key = f"{cls.prefix}:{name}:processing"
            queue = cls(db, name)
            timeout = Spider(db, name).get_field("timeout")
            # redis的scan是可能重复返回同一元素的
            for url, _start in db.hscan_iter(key):
                if time.time() > float(_start) + timeout:  # 过期
                    count += queue.report_error("timeout", url)
        return count

    def report_finish(self, url):
        """标记URL为已完成状态"""
        if not self._db.hdel(self.key_processing, url):
            return False
        self._db.srem(self.key_filter_queue, url)
        sha = utils.RedisScripts.sha1('bloom_cas')
        logger.debug("report_finish", self.name, url)
        return self._db.evalsha(sha, 1, self.name, url)

    def report_error(self, tag, url):
        """标记URL为异常状态"""
        if not self._db.hdel(self.key_processing, url):
            return False
        self._db.sadd(self.key_tags, tag)
        return self._db.lpush(f"{self.prefix_error}:{tag}", url)

    @property
    def tags(self):
        """获取标签列表"""
        return {
            r.decode(): self._db.llen(f"{self.prefix_error}:{r.decode()}")
            for r in self._db.smembers(self.key_tags)
        }

    def get_errors(self, tag, count=0):
        """获取指定标签下的所有异常URL"""
        key = f"{self.prefix_error}:{tag}"
        return [r.decode() for r in self._db.lrange(key, 0, count - 1)]

    def remove_tag(self, tag):
        key = f"{self.prefix_error}:{tag}"
        self._db.srem(self.key_tags, tag)
        return self._db.delete(key)

    def rollback_tag(self, tag, priority):
        """
        将指定标签下的异常URL移至waiting队列中
        返回回滚的URL数量
        """
        if not isinstance(priority, int):
            raise SchedulerError("priority应为int型")
        if priority < 0 or priority >= len(self.key_waiting):
            raise SchedulerError(f"priority可选范围为:{list(range(len(self.key_waiting)))}")
        key_errors = f"{self.prefix_error}:{tag}"
        # 取出并删除异常URL、标签
        pipe = self._db.pipeline()
        pipe.lrange(key_errors, 0, -1)  # 取出所有
        pipe.delete(key_errors)  # 删除队列
        pipe.srem(self.key_tags, tag)  # 删除标签
        res = pipe.execute()
        # 添加至waiting
        urls = res[0]
        if urls:
            self._db.lpush(self.key_waiting[priority], *urls)
        return len(urls)

    @property
    def details(self):
        """队列信息"""
        return {
            'waiting': [self._db.llen(key) for key in self.key_waiting],
            'processing': self._db.hlen(self.key_processing),
            'results': int(self._db.get(self.key_filter_bloom_count) or 0),
            'errors': sum([self._db.llen(f"{self.prefix_error}:{tag}") for tag in self.tags])
        }
