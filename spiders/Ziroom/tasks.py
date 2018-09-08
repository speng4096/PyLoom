import re
import json
import requests
import pytesseract
import urllib.parse
from PIL import Image
from io import BytesIO
from pyloom import tasks
from pyloom.errors import *


class ZiRoomTask(tasks.Task):
    @tasks.retry(5, 0)
    def on_download(self):
        # 解决列表页第一页冲突问题
        page = re.search('\\?p=1', self.url)
        if page is not None:
            self.client.reuse_proxy()
            raise TaskFinish
        try:
            response = self.client.get(
                url=self.url,
                allow_redirects=False,
                headers={
                    "User-Agent": self.ua.chrome
                }
            )
        except (ProxyError, RequestError) as e:
            if self.on_download.count >= 5:  # 重试两次后更换代理
                self.logger.debug("请求错误", e)
                self.client.reload_proxy()
            raise RetryError

        if "请核对您输入的页面地址是否正确" in response.text or "The requested URL could not be retrieved" in response.text:
            if self.on_download.count >= 5:  # 重试两次后更换代理
                self.logger.info("请求次数", self.on_download.count)
                self.client.reload_proxy()
            else:
                self.client.reuse_proxy(5)
            raise RetryError
        if response.status_code == 302:
            if self.on_download.count >= 5:  # 重试两次后更换代理
                self.logger.info("请求次数", self.on_download.count)
                self.client.reload_proxy()
            else:
                self.client.reuse_proxy(5)
            raise RetryError
        if response.status_code == 500:
            raise RetryError
        self.client.reuse_proxy()
        return response

    @staticmethod
    def get_price(response):
        """通过图像匹配返回房租价格"""
        image_url = re.search('static8.ziroom.com/phoenix/pc/images/price/(\w+).png', response.text)[0]
        image = Image.open(BytesIO(requests.get(f'http://{image_url}').content))
        digital_table = pytesseract.image_to_string(image, config='--psm 7')
        offset_list = re.search('\\[((,)?\\[(\w)(,\w)+\\])+\\]', response.text)[0]
        price_list = []
        for offset in offset_list[2:-2].split('],['):
            a = ""
            for offset_num in offset.split(','):
                a = a + (digital_table[int(offset_num)])
            price_list.append(a)
        return price_list


class NLTask(ZiRoomTask):
    filters = "http://(\w+).ziroom.com/z/nl/\S+"

    def on_parse(self):
        """解析链接"""
        house_list = self.response.css.many('#houseList li')
        houses = []
        if self.response.css.one('.nomsg').default(None).text() is None:
            price_list = self.get_price(self.response)
            for house in house_list:
                houses.append(
                    {
                        'price': price_list[len(houses)],
                        'href': house.one('.img a').attrs['href'][2:],
                        'img_src': house.one('.img a img').attrs['src'][2:],
                        'block': house.one('.img a img').attrs.get('alt', None),
                        'name': house.one('.txt h3 a').text(),
                        'site': house.one('.txt h4 a').text(),
                        'detail': house.one('.txt .detail').text(),
                        'room_tags': [tags.text() for tags in house.many('.txt .room_tags span')]
                    }
                )
        else:
            for house in house_list:
                houses.append(
                    {
                        'price': re.search("(\d+)", house.one('.price').text())[0],
                        'href': house.one('.img a').attrs['href'][2:],
                        'img_src': house.one('.img a img').attrs['src'][2:],
                        'block': house.one('.img a img').attrs.get('alt', None),
                        'name': house.one('.txt h3 a').text(),
                        'site': house.one('.txt h4 a').text(),
                        'detail': house.one('.txt .detail').text(),
                        'room_tags': [tags.text() for tags in house.many('.txt .room_tags span')]
                    }
                )
        return houses

    def on_link(self):
        paths = list(set(self.response.re.many('\w+.ziroom.com/z/nl/\S+?.html\\??p?=?\d*')))
        return {
            2: [f'http://{house["href"]}' for house in self.result],
            4: [f'http://{path}' for path in paths]
        }

    def on_save(self):
        self.logger.info(f'抓到房源列表 {self.result}')


class VRTask(ZiRoomTask):
    filters = "http://(\w+).ziroom.com/z/vr/(\w+)"

    def on_parse(self):
        detail_room = {}
        for i in self.response.css.many(".detail_room li"):
            detail = re.sub('\s', '', i.text()).split('：')
            detail_room[detail[0]] = detail[1]
        info = {
            'img': [img.attrs['src'] for img in self.response.css.many('.lidiv img')],
            'room_name': self.response.css.one('.room_name h2').default(None).text(),
            'ellipsis': ' '.join(filter(
                        lambda x: x, self.response.css.one('.room_detail_right .ellipsis').text().split())),
            'room_id': self.response.css.one('#room_id').attrs.get("value"),
            'house_id': self.response.css.one('#house_id').attrs.get("value"),
            'current_city_code': self.response.css.one('#current_city_code').attrs.get('value'),
            'detail_room': detail_room,
            'number': self.response.css.one('.aboutRoom h3').text()[3:],
            'periphery': self.response.css.many('.aboutRoom p')[0].text()[3:],
            'traffic': self.response.css.many('.aboutRoom p')[1].text()[3:]
        }
        roommate = []
        for i in self.response.css.many('.greatRoommate li'):
            roommate.append({
                '性别': i.attrs.get("class")[0],
                '房间号': i.one('.user_top p').text(),
                '星座': i.one('.sign').text()[0:-2],
                '职业': i.one('.jobs').text()[0:-2],
                '入住时间': i.one('.user_bottom p').text(),
            })
        info['roommate'] = roommate
        conf = self.client.get(
            url=f"http://www.ziroom.com/detail/config?house_id={info['house_id']}&id={info['room_id']}",
            headers={
                "User-Agent": self.ua.chrome
            }
        )
        configuration = []
        for i in conf.json['data']:
            if conf.json['data'].get(i) == 1:
                configuration.append(i)
        info['configuration'] = configuration
        cookies = self.response.cookies.get_dict()
        for cookie in cookies:
            if 'nlist' in cookie:
                info['price'] = json.loads(urllib.parse.unquote(
                    self.response.cookies.get_dict()[cookie]))[info["room_id"]]['sell_price']
                break
        return info

    def on_save(self):
        self.logger.info(f'抓到房源信息 {self.result}')
