import re
import time
import uuid
import random
import string
import datetime
from pyloom import tasks, errors


class LaGouJobTask(tasks.Task):
    @staticmethod
    def get_random(const):
        return "".join(random.sample(string.ascii_letters + string.digits, const))

    @staticmethod
    def get_uuid():
        return time.strftime("%Y%m%d%H%M%S-", time.localtime()) + str(uuid.uuid1())

    def get_cookies(self):
        cookies = {
            'LGUID': self.get_uuid(),
            'user_trace_token': '20180705084851-8a154ee4-0f2b-406d-9130-e835805b49ee',
            'X_HTTP_TOKEN': 'c2e6c0237f5362aca8d13748cfdd8274',
            'JSESSIONID': self.get_random(47).upper(),
            'SEARCH_ID': self.get_random(32).lower(),
            'LGSID': self.get_uuid(),
            'PRE_UTM': '',
            'PRE_HOST': '',
            'PRE_SITE': '',
            'PRE_LAND': 'https%3A%2F%2Fwww.lagou.com',
            'LGRID': self.get_uuid()
        }
        return cookies

    @tasks.retry(5, 0)
    def on_download(self):
        """下载页面"""
        if self.buckets.local.get('cookies') is None:
            self.buckets.local.set('cookies', self.get_cookies())
        cookies = self.buckets.local.get('cookies')
        try:
            response = self.client.get(
                url=self.url,
                allow_redirects=False,
                headers={
                    "User-Agent": self.ua.chrome,
                    "Accept-Encoding": "gzip",
                    "Host": "www.lagou.com",
                    "Referer": "https://www.lagou.com/jobs/list_"
                },
                cookies=cookies
            )
        except errors.ProxyError:
            self.logger.info("代理错误")
            raise errors.RetryError
        except errors.RequestError:
            self.logger.info("请求错误")
            raise errors.RetryError

        if response.status_code == 301:
            # 页面被删除
            raise errors.TaskFinish
        elif response.status_code == 302:
            self.logger.info(f"网页被封")
            self.buckets.local.set('cookies', self.get_cookies())
            self.queue.freeze(5)
            raise errors.RetryError
        elif "页面加载中" in response.text or "错误网关" in response.text:
            raise errors.RetryError
        else:
            return response


class JobDetails(LaGouJobTask):
    """职位详情页面"""
    filters = "https://www.lagou.com/jobs/(\d+).html"

    def on_parse(self):
        """提取数据"""
        try:
            publish_time = self.response.css.one(".publish_time").text()[0:-8]
        except errors.TaskError as e:
            return

        if re.match("(\d+):(\d+)", publish_time) is not None:
            publish_time = time.strftime("%Y-%m-%d", time.localtime())
        elif re.match("(\d+)天前", publish_time):
            publish_time = (datetime.date.today() -
                            datetime.timedelta(days=int(publish_time[0]))).strftime('%Y-%m-%d')
        status = 0 if self.response.css.one(".send-CV-btn").text() == "投个简历" else 1
        result = {
            "_id": re.search("(\d+)", self.url).group(0),
            "title": self.response.css.one(".job-name > .name").text(),
            "label": [label.text() for label in self.response.css.many(".labels")],
            "job_request": "".join(request.text() for request in self.response.css.many(".job_request > p > span")),
            "advantage": self.response.css.one(".job-advantage > p").text(),
            "job_bt": self.response.css.one(".job_bt").text(),
            "work_addr": self.response.css.one(".work_addr").text()[0:-8],
            "status": status,
            "job_company": self.response.css.one("#job_company > dt > a > img").attrs["alt"],
            "type": self.response.css.one(".c_feature > li").text(),
            "time": publish_time
        }
        return result

    def on_link(self):
        """提取链接"""
        job_urls = []
        max_id = self.buckets.share.get("max_id") or 4913130  # 爬虫的最大URL
        use_id = self.buckets.share.get("use_id") or -1  # 当前使用的最大URL
        waiting_url_const = self.queue.detail["waiting"][1]  # 当前职位等待队列中的URL数量

        if use_id >= max_id:
            self.queue.interval = 3600

        if waiting_url_const <= 2000:
            # 当等待队列中的URL数量少于1000时，添加URL到等待队列中
            start_id = use_id + 1
            end_id = use_id + 2000 if (use_id + 2000) < max_id else max_id
            for path in range(start_id, end_id):
                job_urls.append(f"https://www.lagou.com/jobs/{path}.html")
            self.buckets.share.set("use_id", use_id + 2000)

        gongsi_urls = [self.response.css.one("#job_company > dt > a").attrs.get("href", None)]
        return {
            0: gongsi_urls,
            1: job_urls
        }

    def on_save(self):
        """保存数据"""
        self.logger.info(f"抓到职位信息 {self.result}")


class GongSiDetails(LaGouJobTask):
    """公司页面详情信息"""
    filters = "https://www.lagou.com/gongsi/(\d+).html"

    def on_parse(self):
        result = {
            "_id": re.search("(\d+)", self.url).group(0),
            "company_abbr": self.response.css.one(".hovertips").text(),
            "company_full_name": self.response.css.one(".hovertips").attrs["title"],
            "type": self.response.css.one(".type + span").text(),
            "process": self.response.css.one(".process + span").text(),
            "number": self.response.css.one(".number + span").text(),
            "address": self.response.css.one(".address + span").default(None).text(),
            "label": [label.text() for label in self.response.css.many(".con_ul_li")],
            "website": self.response.css.one(".hovertips").attrs.get("href", None)
        }
        return result

    def on_save(self):
        self.logger.info(f"抓到公司信息 {self.result}")


class JobsList(LaGouJobTask):
    """工作列表，用于增量拉取职位信息"""
    filters = "https://www.lagou.com/jobs/positionAjax.json?(\w+)"

    @tasks.retry(-1, 0)
    def on_download(self):
        try:
            response = self.client.get(
                url=self.url,
                allow_redirects=False,
                headers={
                    "User-Agent": self.ua.chrome,
                    "DNT": "1",
                    "Host": "www.lagou.com",
                    "Origin": "https://www.lagou.com",
                    "Referer": "https://www.lagou.com/jobs/list_",
                    "X-Anit-Forge-Code": "0",
                    "X-Anit-Forge-Token": None,
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
        except (errors.ProxyError, errors.RequestError):
            raise errors.RetryError

        if response.json['success'] is False:
            self.logger.error(f"列表页发现最新URL出现错误,速率过快")
            raise errors.TaskBreak
        else:
            return response

    def on_parse(self):
        """提取信息"""
        old_max_id = self.buckets.share.get("max_id") or 0
        new_max_id = self.response.json['content']['positionResult']['result'][0]['positionId']
        if old_max_id < new_max_id:
            self.buckets.share.set("max_id", new_max_id)
            self.queue.interval = 0.01
            return [f"https://www.lagou.com/jobs/{new_max_id}.html"]
        else:
            return []

    def on_link(self):
        """提取链接"""
        return {
            1: self.result,
            2: [f"https://www.lagou.com/jobs/positionAjax.json?px=new&needAddtionalResult=false&T={time.time()}"]
        }
