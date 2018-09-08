import json
import redis
import traceback
from .utils import *
from .errors import *
from . import drivers
from .scheduler import Spider
from threading import Thread, Lock

logger = logging.getLogger("proxy")


def proxy_handler(redis_conf, names, name, router, router_lock, driver, **params):
    """
    从驱动获取代理，推送至指定爬虫的代理池中
    每只爬虫有一个代理池，键名为'proxy:proxies:<name>'，list型
        [address1, address2, address3...]
    其中address为str型，结构为：'valid_at:expire_at:address'
        valid_at: 代理生效时间
        expire_at: 代理失效时间
        address: 代理地址
    address在valid_at < now < expire_at可用，并在now > expire_at时被删除
    Args:
        redis_conf: Redis配置
        names: 所有存活代理
        name: 当前代理名，通过name in names判断当前代理是否存活
        router: 路由表，获取代理后，根据路由推送至代理池
        router_lock: router的锁
        driver: 驱动类
        params: 驱动参数
    """
    db = redis.StrictRedis.from_url(redis_conf)
    gen = driver(**params).gen_addresses()
    for is_ok, result in gen:
        with router_lock:
            targets = router.get(name, [])
        logger.debug("代理正在运行", name, targets)
        if not targets:
            logger.info("代理退出，router中没有记录", name, driver)
            break
        if name not in names:
            logger.info("代理退出，names中没有记录", name, driver)
            break
        if is_ok:
            for target in targets:
                length = db.lpush(f"proxy:addresses:{target}", *result)
                logger.info(f"添加代理, 代理:{name}，目标:{target}, 新增数量:{len(result)}, 当前数量:{length}\n", result)
            else:
                time.sleep(1)
        else:
            logger.warning("代理出现异常", name, result)


def get_driver(driver_name):
    """获取并检查驱动是否正确"""
    if not hasattr(drivers, driver_name):
        raise ProxyError("未找到驱动", driver_name)
    driver = getattr(drivers, driver_name)
    if not issubclass(driver, drivers.ProxyDriver):
        raise ProxyError("驱动应继承自ProxyDriver", driver_name)
    if not hasattr(driver, 'title'):
        raise ProxyError("驱动缺少属性", f"{driver_name}.title")
    return driver


def start(redis_conf):
    """
    根据代理配置，维护代理线程池
    代理配置为一个redis dict键，键名为proxy:configs，结构为：
    {
        proxy_name: {
            version: str, // 版本号，版本号变化时，代理线程将会重启
            driver: str, // 驱动名，对应proxy.py中的类
            **params // 驱动参数，将被传递给驱动
        }
    }
    """
    logger.info("代理池已启动")
    db = redis.StrictRedis.from_url(redis_conf)
    threads = {}  # 配置表，{proxy_name: {'version': int, 'thread': Thread}}
    router = {}  # 路由表，{proxy_name: set([spider_name])}
    router_lock = Lock()
    for i in itertools.count():
        try:
            time.sleep(3 if i else 0)
            # 更新路由表，指示代理线程拿到代理后要推给哪些爬虫
            _router = {}
            for spider_name in Spider.names(db):
                spider = Spider(db, spider_name)
                if spider.get_field("status") < 10:
                    logger.debug("忽略未就绪爬虫", spider_name)
                    continue
                last_heartbeat_time = spider.get_field("last_heartbeat_time")
                if time.time() - last_heartbeat_time > 300:
                    logger.debug("忽略长久未运行的爬虫", spider_name)
                    continue
                proxies = Spider(db, spider_name).get_field("proxies")
                if not proxies:
                    logger.debug("忽略未配置代理的爬虫", spider_name)
                    continue
                for proxy_name in proxies:
                    _router.setdefault(proxy_name, set()).add(spider_name)
            with router_lock:
                router.clear()
                router.update(_router)

            # 标记失效线程
            configs = {
                k.decode(): json.loads(v) for k, v in db.hgetall("proxy:configs").items()
            }
            logger.debug("代理配置", configs)
            marked_threads = {}  # 被标记退出的线程，结构同threads
            for proxy_name, fields in threads.items():
                if proxy_name not in configs:
                    logger.info("标记配置被删的代理", proxy_name)
                    marked_threads[proxy_name] = fields
                    continue
                if fields['version'] != configs[proxy_name]['version']:
                    logger.info("标记配置更新的代理", proxy_name)
                    marked_threads[proxy_name] = fields
                    continue
                if proxy_name not in router:
                    logger.info("标记已无爬虫的代理", proxy_name)
                    marked_threads[proxy_name] = fields
                    continue
                if not fields['thread'].is_alive():
                    logger.info("标记异常退出的代理", proxy_name)
                    marked_threads[proxy_name] = fields
                    continue

            # 销毁被标记的线程
            # 线程看见自己没在threads中时会终止
            if marked_threads:
                for proxy_name in marked_threads.keys():
                    del threads[proxy_name]
                    with router_lock:
                        if proxy_name in router:
                            del router[proxy_name]
                logger.info("等待被标记代理线程退出", list(marked_threads.keys()))
                for _ in range(300):
                    alive = any([t['thread'].is_alive() for t in marked_threads.values()])
                    if not alive:
                        break
                    time.sleep(1)
                else:
                    logger.error("被标记代理线程超时仍未退出")
                    threads.update(marked_threads)
                    time.sleep(3)
                    continue
                logger.info("被标记代理线程已全部退出")
            # 启动新线程
            proxy_names_new = set(configs.keys()) - set(threads.keys())
            if proxy_names_new:
                for proxy_name in proxy_names_new:
                    targets = router.get(proxy_name, [])
                    if not targets:
                        logger.debug("代理名下没有爬虫，暂不启动", proxy_name)
                        continue
                    logger.info("启动代理线程", proxy_name)
                    version = configs[proxy_name].pop('version')
                    driver = get_driver(configs[proxy_name].pop('driver'))
                    t = Thread(
                        target=proxy_handler,
                        args=(
                            redis_conf, threads, proxy_name, router, router_lock, driver
                        ),
                        kwargs=(configs[proxy_name]),
                        daemon=True
                    )
                    threads[proxy_name] = {
                        'version': version,
                        'thread': t
                    }
                    t.start()
        except KeyboardInterrupt:
            logger.info("收到Ctrl+C", 'proxy')
            break
        except Exception as e:
            logger.fatal("未处理的异常", type(e), e, '\n', traceback.format_exc())
