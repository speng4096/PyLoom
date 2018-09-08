import furl
import time
import logging
import requests
import traceback
from . import utils

logger = logging.getLogger("drivers")


class ProxyDriver(object):
    """代理驱动的基类，必须继承此类，否则驱动不能被识别"""

    def __init__(self, **kwargs):
        """在代理启动时传入自定义参数"""
        self.url = kwargs['url']
        self.interval = kwargs['interval']
        self.parallel = kwargs['parallel']

    @classmethod
    def get_params(cls):
        """获取自定义参数"""
        template = [
            {
                'name': 'url',
                'title': '代理提取接口？',
                'example': 'http://api.example.com',
                'regex': 'https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]'
            },
            {
                'name': 'interval',
                'title': '每隔多少秒调用一次接口？',
                'type': int,
                'note': "0-无间隔"
            },
            {
                'name': 'parallel',
                'title': '每个代理能被多少线程并发使用？',
                'type': int
            }
        ]
        return utils.template_input(template)

    def gen_addresses(self):
        """
        返回一个生成器，每次迭代时返回一个代理，其格式为：
            valid_at:expire_at:address
        valid_at : 当前时间大于valid_at时代理可用
        expire_at: 当前时间小于expire_at时代理可用，大于expire_at时被删除
        address  : 代理地址，支持http、https、socks5协议
        """
        raise NotImplementedError


class MoGuProxy(ProxyDriver):
    title = '蘑菇API代理'

    def gen_addresses(self):
        logger.info("代理已启动", self.title, self.url)
        while True:
            try:
                time.sleep(self.interval / 2)  # 接口故障时睡眠一半时间
                try:
                    resp = requests.get(self.url, timeout=1)
                except Exception as e:
                    yield False, f"接口请求异常:{e}"
                    continue

                if resp.status_code != 200:
                    yield False, f"接口状态码异常:{resp.status_code}"
                    continue

                try:
                    data = resp.json()
                except Exception:
                    yield False, f"接口返回值非JSON格式"
                    continue

                if int(data.get('code', -1)) != 0:
                    yield False, f'接口返回异常:{data.get("msg", "unknown")}'
                    continue

                expire_at = time.time() + 600
                addresses = [f"0:{expire_at}:http://{i['ip']}:{i['port']}" for i in data.get('msg', [])]
                yield True, addresses * self.parallel
                time.sleep(self.interval / 2)
            except Exception as e:
                logger.error("未处理的异常", type(e), e, '\n', traceback.format_exc())


class MiPuProxy(ProxyDriver):
    title = "米扑开放代理"

    def gen_addresses(self):
        logger.info("代理已启动", self.title, self.url)
        while True:
            try:
                url = furl.furl(self.url)
                url.query.params.set('result_format', 'json')
                time.sleep(self.interval / 2)  # 接口故障时睡眠一半时间
                try:
                    resp = requests.get(url, timeout=1)
                except Exception as e:
                    yield False, f"接口请求异常:{e}"
                    continue

                if resp.status_code != 200:
                    yield False, f"接口状态码异常:{resp.status_code}"
                    continue

                try:
                    data = resp.json()
                except Exception:
                    yield False, f"接口返回值非JSON格式"
                    continue

                if int(data.get('code', -1)) != 0:
                    yield False, f'接口返回异常:{data.get("msg", "unknown")}'
                    continue

                expire_at = time.time() + 60 * 60 * 24 * 30 * 12  # 有效期一年
                addresses = []
                for item in data.get('result', []):
                    scheme = item['http_type'].lower()
                    server = item['ip:port']
                    addresses.append(f"0:{expire_at}:{scheme}://{server}")

                yield True, addresses * self.parallel
                time.sleep(self.interval / 2)
            except Exception as e:
                logger.error("未处理的异常", type(e), e, '\n', traceback.format_exc())
