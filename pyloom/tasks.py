import furl
import json
import redis
import random
import requests
import traceback
import simplejson.errors
from .utils import *
from .errors import *
from lxml import etree
from typing import List
from typing import Union
from . import scheduler, errors
from bs4 import BeautifulSoup, element
from .buckets import LocalBucket, ShareBucket

logger = logging.getLogger("tasks")


class Queue(object):
    """队列控制器"""

    def __init__(self, db, name, url):
        self._spider = scheduler.Spider(db, name)
        self._queue = scheduler.Queue(db, name)
        self.url = url

    @property
    def detail(self):
        return self._queue.details

    @property
    def timeout(self):
        return self._spider.get_field("timeout")

    @timeout.setter
    def timeout(self, value):
        if not isinstance(value, (int, float)):
            raise errors.TaskError("timeout应为int或float型")
        self._spider.set_field("timeout", value)

    @property
    def interval(self):
        return self._spider.get_field("interval")

    @interval.setter
    def interval(self, value):
        if not isinstance(value, (int, float)):
            raise errors.TaskError("interval应为int或float型")
        self._spider.set_field("interval", value)

    def freeze(self, seconds):
        """暂停调度seconds秒"""
        last_pop_time = time.time() + seconds - self.interval
        self._spider.set_field("last_pop_time", last_pop_time)
        logger.info("暂停调度", seconds)

    def stop(self):
        """停止调度，爬虫状态更改为'stop'"""
        logger.info("爬虫状态更改为'stop'")
        self._spider.set_field("status", -2)

    def finish(self):
        """
        提前完成调度，爬虫状态更改为'finish'
        默认情况下，当所有队列均为空时，爬虫状态自动变为'finish'
        """
        logger.info("爬虫状态更改为'finish'")
        self._spider.set_field("status", 0)


class UserAgent(object):
    _ua = None
    _browsers = None

    def __getitem__(self, item):
        if UserAgent._ua is None:
            filename = os.path.join(os.path.dirname(__file__), "user-agent.json")
            with open(filename, encoding='utf8') as f:
                UserAgent._ua = json.load(f)
                UserAgent._browsers = list(UserAgent._ua.keys())
        if item == 'random':
            item = random.choice(UserAgent._browsers)
        return random.choice(UserAgent._ua[item])

    # 便于IDE提示
    @property
    def chrome(self):
        return self["chrome"]

    @property
    def ie(self):
        return self["ie"]

    @property
    def safari(self):
        return self["safari"]

    @property
    def firefox(self):
        return self["firefox"]

    @property
    def android(self):
        return self["android"]

    @property
    def random(self):
        return self["random"]


class CSS(object):
    def __init__(self, root, pattern=":root"):
        if isinstance(root, (element.Tag, type(None))):
            self._root = root
        elif isinstance(root, str):
            self._root = BeautifulSoup(root, "lxml")
        else:
            raise errors.TaskError(f"不支持从'{type(root)}'类型构造CSS")

        self._pattern = pattern
        self._default = ArgDefault

    def __bool__(self):
        return self._root is not None

    def __repr__(self):
        return f"CSS('{self._pattern}')"

    def one(self, pattern):
        node = self._root.select_one(pattern)
        return CSS(node, pattern)  # type: CSS

    def many(self, pattern) -> List['CSS']:
        nodes = self._root.select(pattern)
        return [CSS(node, pattern) for node in nodes]

    def exist(self, pattern):
        return bool(self.one(pattern))

    def default(self, value):
        self._default = value
        return self

    def text(self, regex=None, strip=True, separator=""):
        if self._root is None:
            if self._default is ArgDefault:
                raise errors.TaskError(f"未找到:{repr(self)}")
            else:
                # 默认值不校验格式，直接返回
                return self._default
        _text = self._root.get_text(separator, strip)
        if regex is None or re.match(regex, _text):
            return _text
        else:
            raise errors.TaskError(f"未通过正则校验:{regex}")

    def html(self):
        if self._root is None:
            if self._default is ArgDefault:
                raise errors.TaskError(f"未找到:{repr(self)}")
            else:
                # 默认值不校验格式，直接返回
                return self._default
        return str(self._root)

    @property
    def attrs(self):
        return self._root.attrs


class XPath(object):
    def __init__(self, root, pattern="/*"):
        if isinstance(root, (etree._Element, type(None))):
            self._root = root
        elif isinstance(root, str):
            self._root = etree.HTML(root)
        else:
            raise errors.TaskError(f"不支持从'{type(root)}'类型构造XPath")

        self._pattern = pattern
        self._default = ArgDefault

    def __bool__(self):
        return self._root is not None

    def __repr__(self):
        return f"XPath('{self._pattern}')"

    def one(self, pattern):
        nodes = self._root.xpath(pattern)
        if nodes:
            return XPath(nodes[0])
        else:
            return XPath(None)

    def many(self, pattern):
        nodes = self._root.xpath(pattern)
        return [XPath(node, pattern) for node in nodes]

    def exist(self, pattern):
        return bool(self.one(pattern))

    def default(self, value):
        self._default = value
        return self

    def text(self, regex=None, strip=True):
        if self._root is None:
            if self._default is ArgDefault:
                raise errors.TaskError(f"未找到{repr(self)}")
            else:
                # 默认值不校验格式，直接返回
                return self._default
        _text = self._root.text
        _text = '' if _text is None else _text
        _text = _text.strip() if strip else _text
        if regex is None or re.match(regex, _text):
            return _text
        else:
            raise errors.TaskError(f"未通过正则校验:{regex}")

    @property
    def attrs(self):
        return self._root.attrib


class Regex(object):
    def __init__(self, root):
        self._root = root

    def __bool__(self):
        return self._root is not None

    def many(self, pattern):
        return re.findall(pattern, self._root)


class Response(object):
    def __init__(self, resp: requests.Response):
        self._resp = resp
        self.encoding = "utf-8"
        # 解析器
        self._css = None  # type: CSS
        self._xpath = None  # type: XPath
        self._json = None  # type: dict
        self._re = None  # type: Regex

        self.content = resp.content
        self.status_code = resp.status_code
        self.url = resp.url
        self.furl = furl.furl(resp.url)
        self.request = resp.request  # type: requests.PreparedRequest
        self.history = resp.history  # type: list
        self.cookies = resp.cookies  # type: dict
        self.headers = resp.headers  # type: dict

    @property
    def re(self) -> Regex:
        if not self._re:
            self._re = Regex(self.text)
        return self._re

    @property
    def text(self) -> str:
        self._resp.encoding = self.encoding
        return self._resp.text

    @property
    def json(self) -> dict:
        if self._json:
            return self._json
        try:
            self._json = self._resp.json()
            return self._json
        except simplejson.errors.JSONDecodeError:
            raise errors.JSONDecodeError

    @property
    def css(self) -> CSS:
        if self._css is None:
            self._css = CSS(self.content.decode(self.encoding))
        return self._css

    @property
    def xpath(self) -> XPath:
        if self._xpath is None:
            self._xpath = XPath(self.content.decode(self.encoding))
        return self._xpath

    def __repr__(self):
        return f"Response({self.status_code})"


class Tracking(object):
    """数据埋点"""
    prefix = 'tracking'

    def __init__(self, name, db):
        self._name = name
        self._db = db

    def incr(self, field, amount=1):
        return self._db.incr(f"{self.prefix}:{self._name}:{field}", amount)

    def get(self, field):
        r = self._db.get(f"{self.prefix}:{self._name}:{field}")
        return int(r) if r else None

    @property
    def fields(self):
        return [i.decode().split(":", 2)[2] for i in self._db.keys(f"{self.prefix}:{self._name}:*")]


class Client(object):
    """封装requests，便于包装响应包、掌管代理"""

    def __init__(self, name, db, address=None):
        self._address = address
        self._set_address(address)
        self.name = name
        self.headers = {}
        self._db = db  # type: redis.StrictRedis
        self._session = requests
        self._reuse = False

    def session(self):
        """返回跨请求保留Cookie的客户端"""
        client = Client(self.name, self._db, self._address)
        client._session = requests.session()
        return client

    def request(self, method, url, **kwargs):
        try:
            headers = {**self.headers, **kwargs.pop("headers", {})}
            proxies = {**self.proxies, **kwargs.pop("proxies", {})}
            resp = self._session.request(
                method, url,
                headers=headers,
                proxies=proxies,
                **kwargs
            )
        except requests.exceptions.Timeout as e:
            raise errors.Timeout(e)
        except requests.exceptions.ProxyError as e:
            raise errors.ProxyError(e)
        except requests.exceptions.RequestException as e:
            raise errors.RequestError(e)
        except Exception as e:
            raise e
        return Response(resp)

    def get(self, url, params=None, **kwargs):
        return self.request("get", url, params=params, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        return self.request("post", url, data=data, json=json, **kwargs)

    def head(self, url, **kwargs):
        return self.request("head", url, **kwargs)

    def options(self, url, **kwargs):
        return self.request("options", url, **kwargs)

    def patch(self, url, data=None, **kwargs):
        return self.request("patch", url, data=data, **kwargs)

    def put(self, url, data=None, **kwargs):
        return self.request("put", url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("delete", url, **kwargs)

    def _set_address(self, address):
        if address:
            proxy = address.split(":", 2)[2]
            self.proxies = {
                "http": proxy,
                "https": proxy
            }
            self.proxy = proxy
            self.address = address
            logger.debug("设置代理", proxy)
        else:
            self.proxies = {}
            self.proxy = None
            self.address = None

    def reload_proxy(self) -> bool:
        """丢弃当前代理并更换新代理，若代理池已无可用代理，返回False"""
        recycle = []
        try:
            while True:
                address = self._db.rpop(f"proxy:addresses:{self.name}")
                # 代理池空了
                if not address:
                    raise TaskBreak(0)
                address = address.decode()  # type: str
                _valid_at, _expire_at, _ = address.split(":", 2)
                valid_at, expire_at = float(_valid_at), float(_expire_at)
                # 未到可用时间，还回去
                if valid_at > time.time():
                    recycle.append(address)
                    continue
                # 已到可用时间，但过期了，直接丢弃
                if expire_at < time.time():
                    continue
                self._set_address(address)
                return True
        finally:
            if recycle:
                self._db.lpush(f"proxy:addresses:{self.name}", *recycle)

    def reuse_proxy(self, freeze=0):
        """回收代理，并在freeze秒后可再次被分配"""
        # 只可reuse一次
        if self._reuse:
            return
        else:
            self._reuse = True
        if self.address:
            _, expire_at, proxy = self.address.split(":", 2)
            valid_at = time.time() + freeze
            self._db.lpush(f"proxy:addresses:{self.name}", f"{valid_at}:{expire_at}:{proxy}")
            logger.debug("回收代理", f"{valid_at}:{expire_at}:{proxy}")
            self._set_address(None)

    def __setattr__(self, key, value):
        if key in ['params', 'history']:
            setattr(self._session, key, value)
        else:
            super(Client, self).__setattr__(key, value)


class Buckets(object):
    """数据存储"""

    def __init__(self, local, share):
        self.local = local  # type: LocalBucket
        self.share = share  # type: ShareBucket


class Task(object):
    """描述爬虫行为的抽象类"""
    filters = []

    def __init__(self, name, url, db, address):
        """
        Args:
            name: 爬虫名
            url: 当前URL
            db: redis数据库（用户不可使用）
            address: 代理地址
        """
        self._spider = scheduler.Spider(db, name)
        self._queue = scheduler.Queue(db, name)
        self._db = db  # type: redis.StrictRedis

        self.url = url  # type: str
        self.furl = furl.furl(url)
        self.name = name  # type: str
        self.logger = logging.getLogger(name)
        self.client = Client(name, db, address)
        self.queue = Queue(db, name, url)
        self.ua = UserAgent()
        self.buckets = Buckets(LocalBucket.instance(name), ShareBucket(db, name))
        self.args = self._spider.get_field("args")
        self.lock = self._db.lock  # 分布式锁
        self.tracking = Tracking(name, db)
        self.result = None
        self.response = None  # type: Response

    def on_download(self) -> Response:
        """下载并返回响应包"""
        raise NotImplementedError()

    def on_parse(self) -> dict:
        """提取并返回目标数据"""
        return {}

    def on_link(self) -> Union[list, dict]:
        """
        提取并返回新链接
        Returns:
            links: links可以是list和dict两种类型
                dict: 指定不同的优先级: {priority: urls}
                list: 将links中的url添加到优先级为1的队列中
                      相当于: {1: urls}
        """

    def on_save(self):
        """存储数据"""
        self.logger.debug("on_save", self.result)

    def on_finish(self):
        """已完成"""

    def on_error(self, e) -> bool:
        """
        处理生命周期中抛出的异常（包括on_finish）
        Returns:
            True: 异常已被处理
            False: 异常无法处理
        """
        return False


def execute(task: Task):
    """
    运行task实例并处理所有异常
    Returns:
        links: {priority: urls}
    """
    try:
        task.tracking.incr('on_download')
        task.response = task.on_download()
        task.tracking.incr('on_download_ok')
        task.result = task.on_parse()
        links = task.on_link()
        if isinstance(links, list):
            links = {3: links}
        elif links is None:
            links = {}
        elif not isinstance(links, dict):
            raise errors.TaskError(f"on_link返回值应是list或dict型，而非{type(links)}")
        task.on_save()
        task.on_finish()
        return links
    except errors.TaskFinish:
        logger.debug("TaskFinish", task.url)
        task.on_finish()
        return {}
    except errors.TaskBreak as e:
        logger.debug("TaskBack", e.priority, task.url)
        task._queue.insert(task.url, e.priority)
        return {}
    except errors.TaskError as e:
        task._queue.report_error(e.__class__.__name__, task.url)
        logger.warning("Task报告的异常", str(e), task.url)
        return {}
    except Exception as e:
        if task.on_error(e):
            return {}
        task._queue.report_error("unknown", task.url)
        logger.error(f"Task未处理的异常", "unknown", task.url)
        traceback.print_exc()
        return {}
