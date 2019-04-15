import json
import random
import execjs
import string
import datetime
import re
import os
from pyloom import tasks
from pyloom.errors import *


def get_list_id(opt_id):
    """返回list_id:(opt_id)_(10位随机字符串)"""
    return str(opt_id) + "_" + "".join(random.sample(string.ascii_letters + string.digits, 10))


def get_anti_content(ua):
    path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(path, 'get_anticontent.js'), 'r', encoding='utf-8') as f:
        js = f.read()
    ctx = execjs.compile(js)
    url = "https://mobile.yangkeduo.com/catgoods.html"
    return ctx.call('get_anti', url, ua)


class SearchTask(tasks.Task):
    filters = "https://mobile.yangkeduo.com/classification.html"

    @tasks.retry()
    def on_download(self):
        try:
            ua = self.ua.chrome  # 随机获取ua
            resp = self.client.get(
                url=self.url,
                headers={
                    "User-Agent": ua,
                    'authority': 'mobile.yangkeduo.com',
                    'pragma': 'no-cache',
                    'cache-control': 'no-cache',
                    'upgrade-insecure-requests': '1',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                              'application/signed-exchange;v=b3',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'zh-CN,zh;q=0.9'
                }
            )
        except ProxyError:
            self.client.reload_proxy()
            raise RetryError
        except RequestError:
            raise RetryError
        return resp

    def on_parse(self):
        data = json.loads(self.response.re.many("__NEXT_DATA__.*?__NEXT_LOADED_PAGES")[0][16:-20])
        result = []
        for i in data['props']['pageProps']['data']['operationsData']['detailData']:
            for j in i['cat']:
                result.append(f'https://mobile.yangkeduo.com/proxy/api/v4/operation/{j["optID"]}/groups'
                              f'?offset=0&size=100&opt_type=2&sort_type=DEFAULT&list_id={get_list_id(j["optID"])}'
                              f'&pdduid=0')
        return result

    def on_link(self):
        """解析url,并添加到队列"""
        return {
            4: self.result
        }


class ListTask(tasks.Task):
    filters = "https://mobile.yangkeduo.com/proxy/api/v4/operation/(\w+)"

    @tasks.retry()
    def on_download(self):
        try:
            ua = self.ua.chrome  # 随机获取ua
            url = self.url + f"&anti_content={get_anti_content(ua)}"
            resp = self.client.get(
                url=url,
                headers={
                    "User-Agent": ua,
                    'authority': 'mobile.yangkeduo.com',
                    'pragma': 'no-cache',
                    'cache-control': 'no-cache',
                    'upgrade-insecure-requests': '1',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                              'application/signed-exchange;v=b3',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'zh-CN,zh;q=0.9'
                }
            )
        except ProxyError:
            self.client.reload_proxy()
            raise RetryError
        except RequestError:
            raise RetryError

        return resp

    def on_parse(self):
        goods = []
        for good in self.response.json["goods_list"]:
            goods.append(
                {
                    "thumb_url": good["thumb_url"],
                    "country": good["country"],
                    "goods_name": good["goods_name"],
                    "short_name": good["short_name"],
                    "sales_tip": good["sales_tip"],
                    "cnt": good["cnt"],
                    "goods_id": good["goods_id"],
                    "hd_thumb_url": good["hd_thumb_url"],
                    "hd_url": good["hd_url"],
                    "normal_price": good["normal_price"],
                    "market_price": good["market_price"],
                    "price": good["group"]["price"],
                    "link_url": good["link_url"],
                    "mall_name": good.get('mall_name'),
                    "tag": [i["text"] for i in good["tag_list"]],
                    "updated_at": str(datetime.datetime.now())
                }
            )
        operation = {
            "link_url": [good["link_url"] for good in goods],
            "opt_infos": self.response.json["opt_infos"],
            "opt_id": re.search(r'operation/(\d+)/groups', self.url).group(0).split("/")[1],
            "list_id": re.search(r'&list_id=(\d+)_(\w+)', self.url).group(0).split("=")[1],
            "flip": self.response.json["flip"],
            "next_offset": str(self.response.json["flip"]).split(";")[0]
        }
        return goods, operation

    def on_link(self):
        url = "https://mobile.yangkeduo.com/"

        goods, operation = self.result
        goods_list = [f'{url}{link_url}' for link_url in operation["link_url"]]
        operation_list = [f'{url}/proxy/api/v4/operation/{opt["id"]}/groups?offset=0&size=100&opt_type=2'
                          f'&sort_type=DEFAULT&list_id={get_list_id(opt["id"])}&pdduid=0'
                          for opt in operation["opt_infos"]]
        if operation["flip"] is not None:
            operation_list.append(f'{url}/proxy/api/v4/operation/{operation["opt_id"]}/groups?opt_type=2&size=100'
                                  f'&offset={operation["next_offset"]}&list_id={operation["list_id"]}'
                                  f'&flip={operation["flip"]}&pdduid=0')
        self.logger.debug(goods_list)
        self.logger.debug(operation_list)
        return {
            1: goods_list,
            4: operation_list
        }

    def on_save(self):
        self.logger.debug(self.result[0])


class GoodsTask(tasks.Task):
    filters = "https://mobile.yangkeduo.com/goods.html"

    @tasks.retry()
    def on_download(self):
        try:
            resp = self.client.get(
                url=self.url,
                headers={
                    "User-Agent": self.ua.chrome,
                    'authority': 'mobile.yangkeduo.com',
                    'pragma': 'no-cache',
                    'cache-control': 'no-cache',
                    'upgrade-insecure-requests': '1',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                              'application/signed-exchange;v=b3',
                    'accept-encoding': 'gzip, deflate, br',
                    'accept-language': 'zh-CN,zh;q=0.9'
                }
            )
        except ProxyError:
            self.client.reload_proxy()
            raise RetryError
        except RequestError:
            raise RetryError
        self.logger.debug(resp.status_code)

        if re.search('"initDataObj":{"needLogin":true}', resp.text) is not None:
            raise RetryError
        return resp

    def on_parse(self):
        data = json.loads(self.response.re.many("window.rawData=.*?}};")[0][15:-1])
        return {
            "goods": data["store"]["initDataObj"]["goods"],
            "mall": data["store"]["initDataObj"]["mall"],
            "reviews": data["store"]["initDataObj"]["reviews"],
        }
