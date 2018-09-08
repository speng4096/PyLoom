"""小工具"""
import re
import os
import sys
import time
import uuid
import types
import logging
import readline
import functools
import itertools
import importlib
from pyloom.errors import *
from importlib.machinery import SourceFileLoader
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("utils")


class ArgDefault(object):
    """默认参数"""

    def __bool__(self):
        return False


def patch_logger_format():
    """使logger支持用多个参数构造日志内容"""
    log_bak = logging.Logger._log

    def log(self, level, msg, *args):
        gap = ' '
        out = str(msg) + gap
        for value in args[0]:
            out = out + str(value) + gap
        log_bak(self, level, out, [])

    logging.Logger._log = log


def patch_handler_color(handler):
    """使handler支持根据日志级别输出彩色日志"""
    emit_bak = handler.emit

    def emit(*args):
        level = args[0].levelno
        if level >= 50:
            color = '\x1b[31m'  # red, critical
        elif level >= 40:
            color = '\x1b[31m'  # red, error
        elif level >= 30:
            color = '\x1b[33m'  # yellow, warning
        elif level >= 20:
            color = '\x1b[32m'  # green, info
        elif level >= 10:
            color = '\x1b[35m'  # pink, debug
        else:
            color = '\x1b[0m'  # normal
        args[0].msg = color + args[0].msg + '\x1b[0m'
        return emit_bak(*args)

    handler.emit = emit


class RedisScripts(object):
    """管理redis-lua脚本"""
    _scripts = {}

    @classmethod
    def load(cls, db):
        path = os.path.join(os.path.dirname(__file__), 'lua')
        for filename in os.listdir(path):
            lua_file = os.path.join(path, filename)
            with open(lua_file, encoding="utf-8") as f:
                sha1 = db.script_load(f.read())
                command = filename.split('.')[0]
                RedisScripts._scripts[command] = sha1
                logger.info("缓存Lua脚本", command, sha1)

    @classmethod
    def sha1(cls, command):
        return RedisScripts._scripts[command]


def dict_merge(base: dict, delta: dict, check_not_none=True) -> dict:
    """
    将delta递归合并至base，覆盖同名字段
    若is_not_none为True，
        合并后不应有值为ConfigNotNone，否则抛出ConfigNotNone异常
    Example:
        # 递归合并，修改实参
        >>> base =  {'redis': {'host': '127.0.0.1', 'port': 6379}}
        >>> delta = {'redis': {'host': '192.168.1.1'}}
        >>> dict_merge(base, delta)
        {'redis': {'host': '192.168.1.1', 'port': 6379}}
        >>> base
        {'redis': {'host': '192.168.1.1', 'port': 6379}}

        # 参数check_not_none
        >>> base =  {'redis': {'host': '127.0.0.1', 'port': ConfigNotNone}}
        >>> delta = {'redis': {'host': '192.168.1.1'}}
        >>> dict_merge(base, delta, True)
        Traceback (most recent call last):
        ...
        pyloom.errors.ConfigNotNone: 缺少配置项:'port'
        >>> base =  {'redis': {'host': '127.0.0.1', 'port': ConfigNotNone}}
        >>> dict_merge(base, delta, False)
        {'redis': {'host': '192.168.1.1', 'port': <class 'pyloom.errors.ConfigNotNone'>}}
    """
    if not isinstance(base, dict):
        return delta
    common_keys = set(base).intersection(delta)
    new_keys = set(delta).difference(common_keys)
    for key in common_keys:
        base[key] = dict_merge(base[key], delta[key], check_not_none)
    for key in new_keys:
        base[key] = delta[key]
    if check_not_none:
        for key in base:
            if base[key] is ConfigNotNone:
                raise ConfigNotNone(key)
    return base


def retry(tries=-1, delay=1, max_delay=None, backoff=0, catches=None, error=None):
    """
    自动重试

    当delay=1,backoff=0时，依此休眠：
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    当delay=1,backoff=1时，依此休眠：
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    当delay=1,backoff=2时，依此休眠：
        [1, 2, 5, 10, 17, 26, 37, 50, 65, 82]

    Args:
        tries: 重试次数，（-1:不限重试次数）
        delay: 初始重试秒数
        max_delay: 最大重试秒数（None:不限）
        backoff: 退避指数
        catches: 可被捕捉的异常（RetryError始终可用）
        error: 达到最大重试次数时抛出的异常（默认RetryExceeded）
    """
    if catches is None:
        catches = []

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 记数生成器
            if tries >= 0:
                count = range(tries)
            else:
                count = itertools.count()
            # 处理重试
            for i in count:
                setattr(wrapper, "count", i)
                try:
                    return func(*args, **kwargs)
                except (RetryError, *catches):
                    if backoff == 0:
                        sleep = delay
                    else:
                        sleep = delay + i ** backoff
                    if max_delay:
                        sleep = min(sleep, max_delay)
                    time.sleep(sleep)
            # 重试次数超限
            else:
                if error is None:
                    raise RetryExceeded
                else:
                    raise error

        return wrapper

    return decorator


def template_input(template):
    """
    在命令行提示用户输入配置
    Args:
        template: 配置模板
            例如完成员工信息填写：
            ArgDefault表示必填参数，无默认值
            [
                {
                    "name": 配置名,
                    "title": 配置标题,
                    "example": 示例,
                    "default": 默认值（留空表示必填参数）,
                    "note": 提示信息,
                    "type": 类型转换函数
                }
            ]
    """
    configs = {}
    for fields in template:
        name = fields['name']
        default = fields.get('default', ArgDefault)
        example = fields.get('example', ArgDefault)
        note = fields.get('note', ArgDefault)
        title = fields.get('title', name)
        regex = fields.get('regex', ArgDefault)
        _type = fields.get('type', ArgDefault)
        _range = fields.get('range', ArgDefault)
        if _type is not ArgDefault:
            output = f"{title}[{_type.__name__}]\n"
        else:
            output = f"{title}\n"
        if example is not ArgDefault:
            output += f"示例: {example}\n"
        if note is not ArgDefault:
            output += f"提示: {note}\n"
        output += '➜ '
        first = True
        while True:
            if first:
                var = input(output)
                first = False
            else:
                var = input('➜ ')
            if var:
                # 类型检查
                if _type is not ArgDefault:
                    try:
                        var = _type(var)
                    except ValueError:
                        print(f"参数类型有误，请重试")
                        continue
                # 范围检查
                if _range is not ArgDefault and var not in _range:
                    print(f"参数范围有误，请重试")
                    continue
                # 正则检查
                if regex is not ArgDefault and not re.match(regex, var):
                    print(f"参数格式有误，请重试")
                    continue
                break
            elif not var and default is not ArgDefault:
                var = default
                break
            else:
                print(f"参数不可留空，请重试")
        configs[name] = var
    return configs


def load_py_configs(file) -> dict:
    """
    加载PY格式的配置文件，当配置文件为空时，返回{}
    Args:
        file: 配置文件路径
    """
    if not os.path.exists(file):
        raise ConfigFileNotFoundError(file)
    m = SourceFileLoader(uuid.uuid4().hex, file).load_module()
    return {k: v for k, v in vars(m).items() if not k.startswith('__')}


def load_spider_configs(path) -> dict:
    """
    加载爬虫配置
    Args:
        path: 爬虫目录
    """
    _configs = {
        "seeders": ConfigNotNone,
        "interval": 3,
        "timeout": 120,
        "precision": 0.0001,
        "args": {}
    }
    conf = os.path.join(path, 'configs.py')
    if not os.path.exists(conf):
        raise ConfigFileNotFoundError(f"ERR: 未找到爬虫配置:'{conf}'")
    return dict_merge(_configs, load_py_configs(conf))


def tail(file):
    """模仿linux中的tail命令"""
    try:
        with open(file, 'rb') as f:
            for i in range(1, 11):
                try:
                    f.seek(-(i ** 3), 2)
                except OSError:
                    f.seek(-((i - 1) ** 3), 2)
                    break
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                try:
                    yield line.decode('utf8')
                except UnicodeDecodeError:
                    time.sleep(0.1)
                    continue
    except KeyboardInterrupt:
        pass
