import redis
import signal
import traceback
import threading
import multiprocessing
from . import buckets
from .utils import *
from .tasks import Task, execute
from .scheduler import Spider, Queue

logger = logging.getLogger("worker")


def worker_process(redis_conf, spiders, threads, token_curr, token_new):
    """
    Worker子进程，负责启动线程
    Args:
        redis_conf: redis数据库
        spiders: 所有爬虫配置表，{name: (path, version)}
        threads: 线程数
        token_curr: 新建进程时的token
        token_new: 父进程中最新的token
            当token_curr与token_new不同时，表示父进程已更新了路由，
            线程在完成当前生命周期后需自行退出
    """
    logger.debug("Worker进程已启动")
    # Manager的共享变量在并发启动过多进程时会出现ConnectionRefusedError
    for _ in range(60):
        try:
            spiders.items()
            break
        except Exception:
            pass
    else:
        logger.fatal("Worker进程退出，spiders超时未就绪")
        return

    thread_ids = []
    # 构造路由，{name: [[regex, task]...]}
    routers = {}
    for name, (path, version) in spiders.items():
        tasks = import_tasks(path)
        if tasks:
            routers[name] = tasks
            logger.info("载入爬虫成功", name, version)
        else:
            logger.info("载入爬虫失败，未发现合规Task类", name, version)
    # 启动线程
    try:
        logger.info("正在启动Worker线程")
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # 忽略Ctrl+C
        for thread_index in range(threads):
            thread = threading.Thread(
                target=worker_thread,
                args=(redis_conf, routers, token_curr, token_new, thread_index)
            )
            thread.start()
            thread_ids.append(thread)
        logger.info("Worker线程启动成功")
    except Exception as e:
        logger.fatal("Worker进程结束，启动Worker线程时出现异常", e, '\n', traceback.format_exc())
        return

    for i in itertools.count():
        try:
            # 清理进程内的过期键
            if i % 500 == 0:
                count = buckets.LocalBucket.purge()
                if count:
                    logger.debug(f"完成清理LocalBucket", count)
            # 线程全部退出后，结束进程
            if not any([t.is_alive() for t in thread_ids]):
                logger.info("Worker进程结束，线程已全部退出")
                return
            time.sleep(2)
        except Exception as e:
            logger.fatal("Worker进程异常", e, '\n', traceback.format_exc())
            time.sleep(5)


def worker_thread(redis_conf, routers, token_curr, token_new, thread_index):
    """
    循环：申请任务->执行任务->上报结果
    线程内捕捉所有异常，永不退出（Ctrl+C除外）
    """
    logger.debug("Worker线程已启动")
    db = redis.StrictRedis.from_url(redis_conf)
    pop_failure_count = 0
    while True:
        try:
            # 结束线程
            try:
                if token_curr != token_new.value:
                    logger.info("Worker线程结束，收到退出信号")
                    return
            except ConnectionRefusedError:
                logger.debug("Token未就绪")
                time.sleep(1)
                continue
            except (BrokenPipeError, FileNotFoundError, EOFError):
                logger.info("Worker线程结束，Token已关闭")
                return
            # 从队列中弹出URL
            if not routers:
                logger.info("本地爬虫列表为空，等待加载爬虫")
                while not routers:
                    time.sleep(1)
            keys = list(routers.keys())
            url, name, address = Queue.pop(db, keys)
            if not url:
                if pop_failure_count % 20 == 0:  # 避免日志过多
                    logger.debug("暂无已就绪任务，稍后重试")
                time.sleep(thread_index / 10 + 0.1)
                pop_failure_count += 1
                continue
            logger.info("获得任务", name, url, address)
            pop_failure_count = 0
            # 匹配Task类并执行
            tasks = routers.get(name, None)
            queue = Queue(db, name)
            if tasks is None:
                logger.warning("爬虫匹配失败", name, url)
                queue.report_error("none_spider", url)
                continue
            for regex, task_cls in tasks:
                if not regex.match(url):
                    continue
                # 实例化Task并执行
                task = task_cls(name, url, db, address)
                links = execute(task)
                for priority, urls in links.items():
                    count = queue.add(urls, priority)
                    logger.debug("添加任务", priority, f"{count}/{len(urls)}")
                logger.debug("报告任务完成", queue.report_finish(url), url)
                break
            else:
                logger.warning("任务匹配失败", name, url)
                queue.report_error("none_task", url)
        except Exception as e:
            logger.error("Worker线程异常", e, '\n', traceback.format_exc())
            time.sleep(5)


def import_tasks(path):
    """
    扫描并导入爬虫模块中的Tasks
    Return:
        [[regex, task]...]
    """
    tasks = []
    # 导入模块
    parent = os.path.dirname(path)
    if parent not in sys.path:
        sys.path.append(parent)
    basename = os.path.basename(path)
    try:
        logger.debug("加载爬虫模块", basename)
        _module = importlib.import_module(basename)
    except Exception as e:
        logger.error("加载爬虫模块异常", e, '\n', traceback.format_exc())
        return []
    # 扫描模块中合规的Task子类
    # 何为合规？
    # 1.Task的子类; 2.filters成员; 3.导入无异常; 4.名称不以'__'开头
    for name in dir(_module):
        if name.startswith("__"):
            continue
        var = getattr(_module, name)
        try:
            is_subclass = issubclass(var, Task)
        except TypeError:
            continue
        try:
            if is_subclass:
                if hasattr(var, 'filters') and isinstance(var.filters, (list, tuple, str)):
                    if isinstance(var.filters, str):
                        filters = [var.filters]
                    else:
                        filters = var.filters
                    for regex in filters:
                        tasks.append([re.compile(regex), var])
                        logger.info("导入Task类", var.__name__)
                else:
                    logger.warning("忽略Task类", var.__name__, "filters不合规")
                    continue
            else:
                continue
        except Exception as e:
            logger.error("加载Task类异常", e, '\n', traceback.format_exc())
            continue
    return tasks


def start(spider_path, redis_conf, spider_configs, proxies, processes, threads):
    """
    重置爬虫状态后运行指定爬虫
    Args:
        spider_path: 爬虫目录
        redis_conf: Redis配置
        spider_configs: 爬虫配置
        proxies: 使用代理运行
        processes: 进程数量
        threads: 每个进程的线程数量
    """
    logger.info("正在启动爬虫")
    db = redis.StrictRedis.from_url(redis_conf)
    name = os.path.basename(spider_path)  # 取目录名为爬虫名
    RedisScripts.load(db)
    spider = Spider(db, name)
    # 注册爬虫/更新同名爬虫配置
    logger.info("注册爬虫", name)
    logger.info("爬虫配置", spider_configs)
    spider.upsert(spider_configs['seeders'], spider_configs['interval'],
                  spider_configs['timeout'], spider_configs['precision'],
                  spider_configs['args'], proxies, time.time())
    # 重置爬虫状态
    status = spider.get_field("status")
    if status != 10:
        spider.set_field("status", 10)
        logger.info(f"重置爬虫状态", "{status} -> 10")
    # 回滚'timeout'异常队列
    queue = Queue(db, name)
    logger.debug("清理Redis")
    Queue.purge(db)
    logger.info("回滚超时任务")
    queue.rollback_tag("timeout", 0)
    # 启动Worker
    logger.info("正在启动Worker")
    spiders = multiprocessing.Manager().dict({name: [spider_path, 0]})
    pool = []
    token = multiprocessing.Manager().Value('d', 0)
    for _ in range(processes):
        p = multiprocessing.Process(
            target=worker_process,
            args=(redis_conf, spiders, threads, token.value, token)
        )
        p.start()
        pool.append(p)
    logger.info("Worker启动成功")
    try:
        # 循环检查爬虫状态，当爬虫停止时终止运行
        while True:
            time.sleep(0.2)
            spider = Spider(db, name)
            status = spider.get_field("status")
            if status < 10:
                logger.info("爬虫停止，当前状态为:", Spider.status.get(status, "未知"))
                break
    except KeyboardInterrupt:
        logger.info("收到Ctrl+C", 'main')
        for p in pool:
            p.terminate()
        logger.info("爬虫停止", "Ctrl+C")
    except Exception as e:
        logger.error("爬虫停止", "未知异常", e, '\n', traceback.format_exc())


def start_all(redis_conf, spiders_path, processes, threads):
    """
    启动所有爬虫
    Args:
        redis_conf: Redis配置
        spiders_path: 放置所有爬虫的目录
        processes: 进程数量
        threads: 每个进程的线程数量
    """
