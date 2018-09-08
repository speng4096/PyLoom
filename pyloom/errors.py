class TaskError(Exception):
    """
    Task生命周期中出现的异常
    若某Task抛出此异常，当前URL将被加入异常队列（error）
    """

    def __init__(self, tag):
        self.err = f"TaskError('{tag}')"

    def __str__(self):
        return self.err


class TaskFinish(Exception):
    """提前结束生命周期，并将当前URL加入布隆过滤器"""


class TaskBreak(Exception):
    """提前结束生命周期，并将当前URL归还到任务队列"""

    def __init__(self, priority=0):
        """
        Args:
            priority: 指定队列优先级
        """
        self.priority = priority


class RetryExceeded(TaskError):
    """重试次数超限"""

    def __init__(self):
        self.err = "RetryExceeded"


class RequestError(Exception):
    """请求异常"""


class Timeout(RequestError):
    """请求超时"""


class ProxyError(Exception):
    """代理异常"""


class RetryError(Exception):
    """重试错误，需搭配tasks.retry装饰器使用"""


class JSONDecodeError(ValueError):
    """使用Response().json时出现解码错误"""


class DebuggerError(Exception):
    pass


class SchedulerError(Exception):
    pass


class ConfigError(Exception):
    def __init__(self, name, err=None):
        self.name = name
        self.err = err

    def __str__(self):
        s = f"配置'{self.name}'有误"
        if self.err is not None:
            s += f", {self.err}"
        return s


class ConfigFileNotFoundError(ConfigError, FileNotFoundError):
    def __init__(self, file):
        self.file = file

    def __str__(self):
        return f"未找到配置文件:'{self.file}'"


class ConfigNotNone(ConfigError, ValueError):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"缺少配置项:'{self.name}'"


class BucketError(Exception):
    pass
