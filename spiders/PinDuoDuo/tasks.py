import re
import random
import string
import datetime
from pyloom import tasks
from pyloom.errors import *


def get_list_id(opt_id):
    """返回list_id:(opt_id)_(10位随机字符串)"""
    return str(opt_id) + "_" + "".join(random.sample(string.ascii_letters + string.digits, 10))


class PinDuoDuoTask(tasks.Task):
    """搜索栏"""
    _redis = None
    goods_url = "http://apiv4.yangkeduo.com/api/oakstc/v14/goods/"
    operation_url = "http://apiv4.yangkeduo.com/v4/operation/"

    @tasks.retry(tries=5, backoff=0)
    def on_download(self):
        """下载链接"""
        try:
            resp = self.client.get(
                url=self.url,
                headers={
                    "User-Agent": self.ua.android,
                    "Referer": "Android",
                    "Host": "apiv4.yangkeduo.com"
                }
            )
        except ProxyError:
            self.client.reload_proxy()
            raise RetryError
        except RequestError:
            raise RetryError

        try:
            if "error_code" in resp.json:
                error_code = resp.json.get('error_code', None)
            else:
                error_code = None
        except JSONDecodeError:
            error_code = None

        if error_code == 40001 or resp.status_code == 503 or resp.status_code == 504:
            self.client.reuse_proxy()
            raise RetryError

        if resp.status_code == 403 or resp.status_code == 429:
            self.client.reload_proxy()
            raise RetryError
        else:
            self.client.reuse_proxy()
            return resp


class HomeOperationTask(PinDuoDuoTask):
    """搜索栏"""
    filters = "http://apiv4.yangkeduo.com/api/fiora/v2/home_operations\?pdduid="

    def on_parse(self):
        targets = []
        for childrens in self.response.json:
            targets.append(childrens["id"])
            for children in childrens["children"]:
                targets.append(children["id"])
        return targets

    def on_link(self):
        return {
            4: [f"{self.operation_url}{opt_id}/groups?opt_type=2&size=50&offset=0&list_id={get_list_id(opt_id)}&pdduid="
                for opt_id in self.result]
        }


class OperationTask(PinDuoDuoTask):
    """分类商品结果"""
    filters = "http://apiv4.yangkeduo.com/v4/operation/(\w+)"

    def on_parse(self):
        goods = []
        for good in self.response.json["goods_list"]:
            goods.append(
                {
                    "goods_id": good["goods_id"],
                    "goods_name": good["goods_name"],
                    "thumb_url": good["thumb_url"],
                    "cnt": good["cnt"],
                    "normal_price": good["normal_price"],
                    "market_price": good["market_price"],
                    "price": good["group"]["price"],
                    "updated_at": str(datetime.datetime.now())
                }
            )
        operation = {
            "goods_id": [good["goods_id"] for good in goods],
            "opt_infos": self.response.json["opt_infos"],
            "opt_id": re.search(r'operation/(\d+)/groups', self.url).group(0).split("/")[1],
            "list_id": re.search(r'&list_id=(\d+)_(\w+)', self.url).group(0).split("=")[1],
            "flip": self.response.json["flip"],
            "next_offset": str(self.response.json["flip"]).split(";")[-1]
        }
        return goods, operation

    def on_link(self):
        goods, operation = self.result

        goods_list = [f"{self.goods_url}{goods_id}?goods_id={goods_id}&from=0&pdduid="
                      for goods_id in operation["goods_id"]]
        operation_list = [f'{self.operation_url}{opt_infos["id"]}/groups?opt_type=2&size=50&offset=0'
                          f'&list_id={get_list_id(opt_infos["id"])}&pdduid='
                          for opt_infos in operation["opt_infos"]]

        if operation["flip"] is not None:
            operation_list.append(f'{self.operation_url}{operation["opt_id"]}/groups?opt_type=2&size=50&offset='
                                  f'{operation["next_offset"]}&list_id={operation["list_id"]}'
                                  f'&flip={operation["flip"]}&pdduid=')
        return {
            2: goods_list,
            4: operation_list
        }

    def on_save(self):
        self.logger.info(f'抓到商品列表 {self.result[0]}')


class GoodsTask(PinDuoDuoTask):
    """商品详情接口"""
    filters = "http://apiv4.yangkeduo.com/api/oakstc/v14/goods/(\w+)"

    def on_parse(self):
        _sku = self.response.json["sku"]
        goods_info = {
            "goods_sn": self.response.json["goods_sn"],
            "goods_id": self.response.json["goods_id"],
            "cat_id": self.response.json["cat_id"],
            "goods_name": self.response.json["goods_name"],
            "goods_desc": self.response.json["goods_desc"],
            "market_price": self.response.json["market_price"],
            "is_onsale": self.response.json["is_onsale"],
            "thumb_url": self.response.json["thumb_url"],
            "hd_thumb_url": self.response.json["hd_thumb_url"],
            "image_url": self.response.json["image_url"],
            "goods_type": self.response.json["goods_type"],
            "gallery": [{"id": gallery["id"], "url":gallery["url"]} for gallery in self.response.json["gallery"]],
            "created_at": self.response.json["created_at"],
            "sales": self.response.json["sales"],
            "price": {
                "min_on_sale_group_price": self.response.json["min_on_sale_group_price"],
                "max_on_sale_group_price": self.response.json["max_on_sale_group_price"],
                "min_on_sale_normal_price": self.response.json["min_on_sale_normal_price"],
                "max_on_sale_normal_price": self.response.json["max_on_sale_normal_price"],
                "min_group_price": self.response.json["min_group_price"],
                "max_group_price": self.response.json["max_group_price"],
                "max_normal_price": self.response.json["max_normal_price"],
                "min_normal_price": self.response.json["min_normal_price"],
                "old_min_on_sale_group_price": self.response.json["old_min_on_sale_group_price"],
                "old_max_on_sale_group_price": self.response.json["old_max_on_sale_group_price"],
                "old_min_group_price": self.response.json["old_min_group_price"],
                "old_max_group_price": self.response.json["old_max_group_price"]
            },
            "cat_id_list": [self.response.json["cat_id_1"],
                            self.response.json["cat_id_2"],
                            self.response.json["cat_id_3"]]
        }
        sku = []
        for sku_list in _sku:
            sku.append({
                "sku_id": sku_list["sku_id"],
                "goods_id": sku_list["goods_id"],
                "thumb_url": sku_list["thumb_url"],
                "quantity": sku_list["quantity"],
                "normal_price": sku_list["normal_price"],
                "group_price": sku_list["group_price"],
                "old_group_price": sku_list["old_group_price"],
                "specs": sku_list["specs"]
            })
        goods_info["sku"] = sku
        return goods_info

    def on_save(self):
        self.logger.info(f'抓到商品信息 {self.result}')
