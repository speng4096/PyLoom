from pyloom.tasks import *


class DouBanTask(Task):
    filters = ["^https://movie.douban.com/top250(\?start=\d+)?$"]

    def on_download(self):
        return self.client.get(
            url=self.url,
            headers={
                "Host": "movie.douban.com",
                "User-Agent": self.ua.chrome
            }
        )

    def on_parse(self):
        nodes = self.response.css.many("div.article ol > li")
        return [{
            "title": node.one("span.title").text(),
            "rating": node.one("span.rating_num").text(),
            "quote": node.one("p.quote > span.inq").text()
        } for node in nodes]

    def on_link(self):
        if self.url.endswith("top250"):
            return [f"{self.url}?start={i}" for i in range(25, 250, 25)]

    def on_save(self):
        for movie in self.result:
            self.logger.info("抓到电影", movie)
