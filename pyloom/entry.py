"""
程序入口
解析命令行参数、配置文件参数，启动对应模块
所有有关参数解析的操作应当在这里完成
"""
import json
import redis
import daemon
import signal
import psutil
import datetime
import argparse
import daemon.pidfile
from .utils import *
from .errors import *
from tabulate import tabulate
from .scheduler import Spider, Queue
from . import drivers, worker, proxy, tasks

logger = logging.getLogger("entry")


def set_defaults(options):
    """设置默认值"""
    # 设置日志
    if hasattr(options, 'log'):
        if options.log:
            options.log = os.path.abspath(os.path.expanduser(options.log))
        else:
            root_path = os.path.dirname(os.path.dirname(__file__))
            options.log = os.path.join(root_path, 'logs')
            os.makedirs(options.log, exist_ok=True)
    logging.getLogger("requests").setLevel(logging.WARNING)
    patch_logger_format()
    if hasattr(options, 'level'):
        logging.basicConfig(level=options.level.upper())
    # 设置爬虫目录
    if hasattr(options, 'spider'):
        options.spider = os.path.abspath(os.path.expanduser(options.spider))
        setattr(options, 'name', os.path.basename(options.spider))


def set_console_logger():
    """设置在控制台中输出日志"""
    fmt = fr'[%(levelname)1.1s][%(asctime)s.%(msecs)03d][%(name)s] %(message)s'
    date_fmt = '%y%m%d %H:%M:%S'
    formatter = logging.Formatter(fmt, date_fmt)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    patch_handler_color(handler)
    logging.root.handlers = [handler]


def set_file_logger(options, filename):
    """
    设置使用文件记录日志
    需在DaemonContext中调用此函数，否则DaemonContext会关闭日志文件导致启动失败
    """
    fmt = fr'[%(levelname)1.1s][%(asctime)s.%(msecs)03d][%(name)s] %(message)s'
    date_fmt = '%y%m%d %H:%M:%S'
    formatter = logging.Formatter(fmt, date_fmt)
    handler = TimedRotatingFileHandler(
        filename=os.path.join(options.log, filename),
        backupCount=options.backup,
        when="MIDNIGHT"
    )
    handler.setFormatter(formatter)
    logging.root.handlers = [handler]


def handler_common_stop(options, pid_name):
    """停止指定进程"""
    pidfile = os.path.join(options.log, pid_name)
    if not os.path.exists(pidfile):
        return "后台进程未启动"
    with open(pidfile) as f:
        pid = int(f.read())
    if pid:
        os.kill(pid, signal.SIGINT)
        print(f"已发出信号，等待进程退出，pid={pid}")
        # 等待进程退出
        for _ in range(32):
            if not psutil.pid_exists(pid):
                return "OK"
            time.sleep(1)
        else:
            return f"ERR: 进程超时未退出，pid={pid}"
    else:
        return "OK"


def handler_common_tail(options, filename):
    """查看指定进程的日志"""
    logfile = os.path.join(options.log, filename)
    if not os.path.exists(logfile):
        return "没有日志"
    for line in tail(logfile):
        print(line, end='')


def parse_args(args):
    """
    从字符串中解析出多个参数

    >>> parse_args(" a,b，c,   ")
    ['a', 'b', 'c']
    """
    if not args:
        return []
    args = args.replace("，", ",")
    return [a.strip() for a in args.split(",") if a.strip()]


def handler_proxy_run(options):
    """启动代理池节点"""
    if options.damon:
        pidfile = daemon.pidfile.PIDLockFile(os.path.join(options.log, 'proxy.pid'))
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            if psutil.pid_exists(pid):
                return f"已有实例正在运行，pid={pid}"
            else:
                pidfile.break_lock()
        print("OK")
        with daemon.DaemonContext(pidfile=pidfile, stderr=sys.stderr):
            set_file_logger(options, "proxy")
            return proxy.start(options.redis)
    else:
        return proxy.start(options.redis)


def handler_proxy_add(options):
    """添加代理"""
    db = redis.StrictRedis.from_url(options.redis)
    # 扫描所有驱动
    driver_name_to_title = {}
    for driver_name, var in vars(drivers).items():
        try:
            if issubclass(var, drivers.ProxyDriver) \
                    and var is not drivers.ProxyDriver \
                    and hasattr(var, 'title'):
                driver_name_to_title[driver_name] = getattr(var, 'title')
        except TypeError:
            pass
    if not driver_name_to_title:
        return "ERR: 无可用驱动"
    drivers_names = list(driver_name_to_title.items())
    # 询问用户，选择驱动
    print("请选择代理驱动 (填写序号或英文名称)")
    print('\n'.join([f"{i}. {k}, {v}" for i, (k, v) in enumerate(drivers_names)]))
    s = input('➜ ')
    driver_name = driver_name_to_title.get(s) and s
    if driver_name is None:
        try:
            driver_name = drivers_names[int(s)][0]
        except (ValueError, KeyError, IndexError):
            return "ERR: 序号或名称错误"
    print("当前驱动为: ", driver_name)
    driver_cls = getattr(drivers, driver_name)
    # 询问配置
    proxy_name = template_input([{
        "name": "name",
        "title": "请为当前配置设置独一无二的名称"
    }])['name']
    proxy_params = driver_cls.get_params()
    # 检查配置名是否重复
    if db.hexists("proxy:configs", proxy_name):
        s = input(f"配置'{proxy_name}'已存在，是否覆盖 (Y/N) ")
        if s.upper() != 'Y':
            return 'Bye~'
    # 写入配置
    proxy_params['version'] = int(time.time())
    proxy_params['driver'] = driver_cls.__name__
    db.hset("proxy:configs", proxy_name, json.dumps(proxy_params))
    return 'OK'


def handler_proxy_remove(options):
    """删除代理"""
    db = redis.StrictRedis.from_url(options.redis)

    if options.name == 'all':
        count = db.delete("proxy:configs", *db.keys("proxy:addresses:*"))
    else:
        count = db.hdel("proxy:configs", options.name)
        count += db.delete(f"proxy:addresses:{options.name}")
    if count:
        return 'OK'
    else:
        return '没有代理'


def handler_proxy_list(options):
    """列出所有代理"""
    db = redis.StrictRedis.from_url(options.redis)

    configs = db.hgetall("proxy:configs")
    if not configs:
        return "没有代理"
    configs = {k.decode(): json.loads(v) for k, v in configs.items()}
    data = [(k, v['driver']) for k, v in configs.items()]
    headers = ['配置名', '驱动']
    return tabulate(data, headers, 'presto', showindex='always')


def handler_run(options):
    """运行爬虫"""
    db = redis.StrictRedis.from_url(options.redis)
    spider_configs = load_spider_configs(options.spider)

    proxies = parse_args(options.proxy)
    if proxies:
        for proxy_name in proxies:
            if not db.hexists("proxy:configs", proxy_name):
                return f"ERR: 未找到代理'{proxy_name}'"
        logger.info("使用代理运行", proxies)

    if not os.path.exists(os.path.join(options.spider, '__init__.py')):
        return "ERR: 未找到爬虫入口:'__init__.py'"

    if options.clear:
        logger.info("清空队列与代理数据")
        Spider(db, options.name).clear_proxy()
        Spider(db, options.name).clear_queue()

    if options.damon:
        pidfile = daemon.pidfile.PIDLockFile(os.path.join(options.log, f'{options.name}.pid'))
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            if psutil.pid_exists(pid):
                return f"已有实例正在运行，pid={pid}"
            else:
                pidfile.break_lock()
        logger.info("转入后台运行")
        with daemon.DaemonContext(pidfile=pidfile, stderr=sys.stderr):
            set_file_logger(options, options.name)
            return worker.start(
                options.spider, options.redis, spider_configs,
                proxies, options.processes, options.threads
            )
    else:
        return worker.start(
            options.spider, options.redis, spider_configs,
            proxies, options.processes, options.threads
        )


def handler_remove(options):
    """清除数据"""
    db = redis.StrictRedis(options.redis)
    spider = Spider(db, options.name)
    if options.target == 'queue':
        count = spider.clear_queue()
        return f"已清除{count}条队列数据"
    elif options.target == 'proxy':
        count = spider.clear_proxy()
        if count:
            return "已清除代理数据"
        else:
            return "没有代理数据"
    else:
        return f"无法清理:{options.target}"


def handler_top(options):
    """查看统计"""
    db = redis.StrictRedis.from_url(options.redis)
    tracking = tasks.Tracking(options.name, db)
    lasts = {field: tracking.get(field) for field in sorted(tracking.fields)}
    try:
        while True:
            print(f'[{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]', end=' ')
            count = db.llen(f"proxy:addresses:{options.name}")
            print(f'proxy:{count}', end='; ')
            fields = sorted(tracking.fields)
            for field in fields:
                last = lasts.get(field, None)
                current = tracking.get(field)
                lasts[field] = current
                if last is None:
                    print(f"{field}:None", end='; ')
                else:
                    print(f"{field}:{round((current-last)/options.interval, 1)}", end='; ')
            print(end='\n')
            time.sleep(options.interval)
    except KeyboardInterrupt:
        return


def handler_tag_list(options):
    """查看所有异常标签"""
    db = redis.StrictRedis.from_url(options.redis)
    if not Spider(db, options.name).exists():
        return "爬虫不存在"
    queue = Queue(db, options.name)
    if options.tag:
        data = [(d,) for d in queue.get_errors(options.tag, 0)]
        return tabulate(data, ['URL'], 'presto', showindex='always')
    else:
        tags = queue.tags
        if not tags:
            return "没有标签"
        else:
            data = sorted(tags.items(), key=lambda t: t[1], reverse=True)
            headers = ['标签', '数量']
            return tabulate(data, headers, 'presto', showindex='always')


def handler_tag_remove(options):
    """移除异常标签"""
    db = redis.StrictRedis.from_url(options.redis)
    if not Spider(db, options.name).exists():
        return "爬虫不存在"
    queue = Queue(db, options.name)
    if options.tags == 'all':
        tags = queue.tags
    else:
        tags = parse_args(options.tags)
    if not tags:
        return '没有标签'
    for tag in tags:
        if queue.remove_tag(tag):
            print(f"已删除标签'{tag}'")
        else:
            print(f"未找到标签'{tag}'")
    return "OK"


def handler_tag_rollback(options):
    """回滚异常标签下的所有任务"""
    db = redis.StrictRedis.from_url(options.redis)
    if not Spider(db, options.name).exists():
        return "爬虫不存在"
    queue = Queue(db, options.name)
    if options.tags == 'all':
        tags = queue.tags
    else:
        tags = parse_args(options.tags)
    if tags:
        for tag in tags:
            count = queue.rollback_tag(tag, 0)
            return f"回滚'{tag}', 数量:{count}, 队列优先级:0"
    else:
        return "未指定标签"


def main():
    # parents
    log = argparse.ArgumentParser(add_help=False)
    log.add_argument('-l', '--level', default='info', help='日志级别')
    log.add_argument('--log', help='存放日志文件的目录')
    log.add_argument('--backup', type=int, default=3, help='日志文件保留数量')
    spider = argparse.ArgumentParser(add_help=False)
    spider.add_argument('-s', '--spider', default='./', help='指定爬虫目录')
    db = argparse.ArgumentParser(add_help=False)
    db.add_argument('-r', '--redis', default='redis://127.0.0.1:6379/0', help='指定redis地址')

    # pyloom
    node = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    node.set_defaults(module=None)
    node_modules = node.add_subparsers()

    # pyloom run
    node_run = node_modules.add_parser('run', help='运行爬虫', parents=[log, spider, db])
    node_run.set_defaults(module='run')
    node_run.add_argument('-C', '--clear', action="store_true", help='清空爬虫数据后运行')
    node_run.add_argument('--proxy', help='使用指定代理运行，逗号分隔多个代理')
    node_run.add_argument('-d', '--damon', action="store_true", help='作为守护进程运行')
    node_run.add_argument('-p', '--processes', default=2, type=int, help='子进程数量')
    node_run.add_argument('-t', '--threads', default=40, type=int, help='每个子进程的线程数量')
    # pyloom stop
    node_stop = node_modules.add_parser('stop', help='停止后台运行的爬虫', parents=[spider])
    node_stop.set_defaults(module='stop')
    # pyloom tail
    node_tail = node_modules.add_parser('tail', help='查看日志文件', parents=[log, spider])
    node_tail.set_defaults(module='tail')
    # pyloom top
    node_top = node_modules.add_parser('top', help='查看统计', parents=[spider, db])
    node_top.set_defaults(module='top')
    node_top.add_argument('-i', '--interval', default=10, type=int, help='抽样间隔')
    # pyloom remove
    node_remove = node_modules.add_parser('remove', help='清除爬虫数据')
    node_remove.set_defaults(module='remove')
    node_remove.set_defaults(target=None)
    node_remove_targets = node_remove.add_subparsers()
    # pyloom remove queue
    node_remove_queue = node_remove_targets.add_parser('queue', help='清除队列数据', parents=[spider, db])
    node_remove_queue.set_defaults(target='queue')
    # pyloom remove proxy
    node_remove_proxy = node_remove_targets.add_parser('proxy', help='清空代理池', parents=[spider, db])
    node_remove_proxy.set_defaults(target='proxy')
    # pyloom tag
    node_tag = node_modules.add_parser('tag', help='标签管理')
    node_tag.set_defaults(module='tag')
    node_tag.set_defaults(command=None)
    node_tag_commands = node_tag.add_subparsers()
    # pyloom tag list
    node_tag_list = node_tag_commands.add_parser('list', help='查看标签', parents=[spider, db])
    node_tag_list.set_defaults(command='list')
    node_tag_list.add_argument('tag', nargs='?', help='列出指定标签的内容，留空显示标签列表')
    # pyloom tag remove
    node_tag_remove = node_tag_commands.add_parser('remove', help='清除标签', parents=[spider, db])
    node_tag_remove.set_defaults(command='remove')
    node_tag_remove.add_argument('tags', help='被清除的标签，逗号分隔多个标签')
    # pyloom rollback :tag
    node_tag_rollback = node_tag_commands.add_parser('rollback', help='回滚标签', parents=[spider, db])
    node_tag_rollback.set_defaults(command='rollback')
    node_tag_rollback.add_argument('tags', help='被回滚的标签，逗号分隔多个标签')

    # pyloom proxy
    node_proxy = node_modules.add_parser('proxy', help='代理节点')
    node_proxy.set_defaults(module='proxy')
    node_proxy.set_defaults(command=None)
    node_proxy_commands = node_proxy.add_subparsers()
    # pyloom proxy run
    node_proxy_run = node_proxy_commands.add_parser('run', help='启动代理节点', parents=[log, db])
    node_proxy_run.set_defaults(command='run')
    node_proxy_run.add_argument('-d', '--damon', action="store_true", help='作为守护进程运行')
    # pyloom proxy stop
    node_proxy_stop = node_proxy_commands.add_parser('stop', help='停止节点', parents=[log])
    node_proxy_stop.set_defaults(command='stop')
    # pyloom proxy tail
    node_proxy_tail = node_proxy_commands.add_parser('tail', help='查看日志', parents=[log])
    node_proxy_tail.set_defaults(command='tail')
    # pyloom proxy add
    node_proxy_add = node_proxy_commands.add_parser('add', help='添加代理', parents=[db])
    node_proxy_add.set_defaults(command='add')
    # pyloom proxy remove
    node_proxy_remove = node_proxy_commands.add_parser('remove', help='删除指定代理', parents=[db])
    node_proxy_remove.set_defaults(command='remove')
    node_proxy_remove.add_argument('name', help='欲删除的代理名称，all表示所有代理')
    # pyloom proxy list
    node_proxy_list = node_proxy_commands.add_parser('list', help='列出所有配置', parents=[db])
    node_proxy_list.set_defaults(command='list')

    # 路由至对应模块
    options = node.parse_args()
    try:
        set_defaults(options)
        set_console_logger()
        if options.module == 'proxy':
            if options.command == 'run':
                return handler_proxy_run(options)
            elif options.command == 'stop':
                return handler_common_stop(options, 'proxy.pid')
            elif options.command == 'tail':
                return handler_common_tail(options, 'proxy')
            elif options.command == 'add':
                return handler_proxy_add(options)
            elif options.command == 'remove':
                return handler_proxy_remove(options)
            elif options.command == 'list':
                return handler_proxy_list(options)
            else:
                return node_proxy.print_help()
        elif options.module == 'run':
            return handler_run(options)
        elif options.module == 'stop':
            return handler_common_stop(options, f'{options.name}.pid')
        elif options.module == 'remove':
            return handler_remove(options)
        elif options.module == 'top':
            return handler_top(options)
        elif options.module == 'tail':
            return handler_common_tail(options, options.name)
        elif options.module == 'tag':
            if options.command == 'list':
                return handler_tag_list(options)
            elif options.command == 'remove':
                return handler_tag_remove(options)
            elif options.command == 'rollback':
                return handler_tag_rollback(options)
            else:
                return node_tag.print_help()
        else:
            return node.print_help()
    except ConfigFileNotFoundError as e:
        return f'ERR: {str(e)}'
