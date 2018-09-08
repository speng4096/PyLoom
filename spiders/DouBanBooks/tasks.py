from pyloom.errors import *
from pyloom.tasks import Task, CSS, retry


class BaseTask(Task):
    @retry(10, 0)
    def on_download(self):
        """下载页面"""
        try:
            response = self.client.get(
                url=self.url,
                allow_redirects=False,
                headers={
                    "Host": "book.douban.com",
                    "User-Agent": self.ua.chrome
                },
                timeout=8
            )
        except (ProxyError, RequestError):
            self.client.reload_proxy()
            raise RetryError
        # 检查是否被封禁
        if response.status_code == 200:
            s = 'window.location.href="https://sec.douban.com/a'
            if s in response.text:
                self.logger.warning("IP被封禁:200", self.client.address)
                self.client.reuse_proxy(300)
            else:
                self.client.reuse_proxy()
                return response
        elif response.status_code == 302:
            self.logger.warning("IP被封禁:302", self.client.address)
            self.client.reuse_proxy(300)
        else:
            self.logger.warning("请求错误", response.status_code)
        self.client.reload_proxy()
        raise RetryError

    def parse_tag_urls(self):
        """提取页面中所有的标签链接"""
        # 获取所有标签详情页的相对路径
        paths = self.response.re.many("/tag/\w+")
        # 构造每个标签前50页的标签详情页链接，优先级为2:最低
        return [
            f"https://book.douban.com{path}?start={i*20}&type=R"
            for path in paths for i in range(50)
        ]


class BookDetailsTask(BaseTask):
    """图书详情页"""
    filters = ["https://book.douban.com/subject/(\d+)/"]

    def on_parse(self):
        css = self.response.css
        # 书籍基本信息
        info = {}
        for line in css.one("div#info").html().split("<br/>"):
            items = [
                ' '.join(s.split())
                for s in CSS(line).text(separator=" ").split(":", 1)
                if s.strip()
            ]
            if len(items) == 2:
                info[items[0]] = items[1]
        result = {
            "title": css.one("h1 > span").text(),
            "cover": css.one("div#mainpic img").attrs.get("src", None),
            "info": info,
            "rating_num": css.one("div.rating_self > strong.rating_num").text() or None,
            "rating_people": css.one("a.rating_people > span").default(None).text(),
            "intro": css.one("div#link-report div.intro > p").default(None).text(separator="\n"),
            "tags": [n.text() for n in css.many("div#db-tags-section a")],
        }
        return result

    def on_link(self):
        books = self.response.re.many("https://book.douban.com/subject/\d+/")
        # 指定优先级
        return {
            0: books,
            4: self.parse_tag_urls()
        }

    def on_save(self):
        self.logger.info("抓到新书", self.result)


class TagsTask(BaseTask):
    """热门标签页"""
    filters = ["https://book.douban.com/tag/\?view=cloud"]

    def on_link(self):
        return self.parse_tag_urls()


class TagDetailsTask(BaseTask):
    """标签详情页"""
    filters = ["https://book.douban.com/tag/(\w+)\?start=(\d+)&type=R"]

    def on_link(self):
        books = self.response.re.many("https://book.douban.com/subject/\d+/")
        return {
            0: books,
            4: self.parse_tag_urls()
        }
