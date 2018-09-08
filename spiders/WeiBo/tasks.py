import re
import datetime
import itertools
from pyloom import tasks
from pyloom.errors import *


class PWATask(tasks.Task):
    _redis = None

    def __init__(self, *args, **kwargs):
        super(PWATask, self).__init__(*args, **kwargs)
        self.uid = self.url.split(":")[1]
        self.client.headers = {
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'https://m.weibo.cn/profile/{self.uid}',
            'MWeibo-Pwa': '1',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': self.ua.chrome
        }

    @tasks.retry(tries=16, delay=0, backoff=0)
    def download(self, url, params):
        """下载并判断是否被封禁"""
        try:
            resp = self.client.get(url, params, timeout=8)
        except (ProxyError, RequestError) as e:
            if self.download.count >= 3:  # 重试两次后更换代理
                self.logger.debug("请求错误", e)
                self.client.reload_proxy()
            raise RetryError
        try:
            errno = resp.json.get('errno', None)
        except JSONDecodeError:
            errno = None
        if resp.status_code == 418 or (resp.status_code == 403 and errno == "100005"):
            self.logger.debug("响应包错误，IP已被封禁")
            self.client.reuse_proxy(150)
            self.client.reload_proxy()
            raise RetryError
        elif errno == "20003":
            self.logger.debug("响应包错误，用户不存在", self.uid)
            raise TaskFinish()
        elif resp.status_code != 200:
            self.logger.debug(f"响应包错误，状态码:{resp.status_code}", self.uid)
            if self.download.count >= 3:
                self.client.reload_proxy()
            raise RetryError
        elif errno is not None:
            msg = resp.json['msg']
            self.logger.debug(f"响应包错误，errno={errno}，msg={msg}", self.uid)
            raise TaskError("msg:" + msg)
        else:
            self.client.reuse_proxy(0)
            return resp


class UserTask(PWATask):
    """用户资料"""
    filters = "user:\w+"

    def on_download(self):
        return self.download('https://m.weibo.cn/profile/info', {'uid': self.uid})

    def parse_text(self, _text):
        """转换微博内容以节约空间"""

        # 将表情包转为:[拜拜]
        def replacer_first(match):
            return match.groups()[0]

        text = re.sub(
            r'<span[^>]+class="url-icon">\s*<img alt="([^"]+)".+?</span>', replacer_first, _text
        )

        # 将链接转为:{title}(url)
        # title一般为话题
        def replacer_link(match):
            groups = match.groups()
            return f"{{{groups[1]}}}({groups[0]})"

        text = re.sub(
            r'<a[^>]+href="([^"]+)".*?>\s*<span class="surl-text">([^<>]+)</span>\s*</a>',
            replacer_link, text
        )
        # 将@连接转为: @XXX
        text = re.sub(r'<a href=[^>]+>(@[^<>]+)</a>', replacer_first, text)
        # 将<br />转为\n
        text = text.replace("<br />", "\n")
        return text

    def parse_status(self, _status):
        """递归提取源微博与被转发微博"""
        status = {
            'mid': int(_status['id']),
            'uid': _status['user']['id'],
            'text': self.parse_text(_status['text']),
            'reposts_count': _status['reposts_count'],
            'comments_count': _status['comments_count'],
            'attitudes_count': _status['attitudes_count'],
            'source': _status['source'],
            'updated_at': datetime.datetime.now(),
            'created_at': datetime.datetime.strptime(
                _status['created_at'], "%a %b %d %H:%M:%S %z %Y"),
        }
        retweeted_status = _status.get('retweeted_status', None)
        if retweeted_status:  # 转发
            status['pmid'] = _status.get('pid', 0)
            status['smid'] = int(retweeted_status['id'])
            status['suid'] = int(retweeted_status['user']['id'])
            repost = status
            status, _ = self.parse_status(retweeted_status)
            return status, repost
        else:  # 原创
            status['images'] = _status['pic_ids']
            status['is_long_text'] = _status['isLongText']
            return status, None

    def on_parse(self):
        # 用户信息
        _user = self.response.json['data']['user']
        user = {
            'uid': _user['id'],
            'screen_name': _user['screen_name'],
            'statuses_count': _user['statuses_count'],
            'verified_type': _user['verified_type'],
            'verified_type_ext': _user.get('verified_type_ext', -1),
            'description': _user['description'],
            'gender': _user['gender'],
            'mbtype': _user['mbtype'],
            'urank': _user['urank'],
            'mbrank': _user['mbrank'],
            'followers_count': _user['followers_count'],
            'follow_count': _user['follow_count'],
            'profile_image_id': _user['profile_image_url'].rsplit("/", 1)[1].split(".")[0],
            'status': 0,
            'updated_at': datetime.datetime.now()
        }
        # 最近微博
        statuses = []
        reposts = []
        for _status in self.response.json['data']['statuses']:
            status, repost = self.parse_status(_status)
            if status:
                statuses.append(status)
            if repost:
                reposts.append(repost)

        return user, statuses, reposts

    def on_link(self):
        return {
            3: [f'follow:{self.uid}'],
            4: [f'fan:{self.uid}']
        }

    def on_save(self):
        self.logger.info("抓到用户信息", self.result[0])
        if self.result[1]:
            self.logger.info("抓到原创微博", self.result[1])
        if self.result[2]:
            self.logger.info("抓到转发微博", self.result[2])


class ContainerTask(PWATask):
    """解析关注和粉丝列表的响应包"""

    def on_parse(self):
        targets = []
        for page in self.response:
            cards = page.json['data']['cards']
            for card in cards:
                style = card.get('card_style', None)
                group = card['card_group']
                if style is None:  # 普通用户
                    targets.extend(g['user']['id'] for g in group)
                elif style == 1:  # 推荐用户
                    if len(group) == 3 and 'scheme' in group[2]:  # 相关大V用户
                        if 'users' in group[1]:
                            ids = [user['id'] for user in group[1]['users']]
                        elif 'user' in group[1]:
                            ids = [group[1]['user']['id']]
                        else:
                            ids = []
                    else:  # 大V用户
                        ids = [g['user']['id'] for g in group if 'user' in g]
                    targets.extend(ids)
                else:
                    raise TaskError(f"card_style={style}")
        _targets = []
        for t in targets:
            try:
                _targets.append(int(t))
            except ValueError:
                pass
        return _targets

    def on_link(self):
        return {1: [f"user:{uid}" for uid in self.result]} if self.result else {}


class FollowerTask(ContainerTask):
    """关注列表"""
    filters = "follow:\w+"

    def on_download(self):
        pages = []
        url = "https://m.weibo.cn/api/container/getIndex"
        for page_id in itertools.count(1):
            params = {"containerid": f"231051_-_followers_-_{self.uid}"}
            if page_id != 1:
                params['page'] = page_id
            resp = self.download(url, params)
            if resp.json['ok'] == 0:  # 已到最后一页
                break
            pages.append(resp)
        return pages

    def on_save(self):
        self.logger.info("抓到关注列表", self.result)


class FanTask(ContainerTask):
    """粉丝列表"""
    filters = "fan:\w+"

    def on_download(self):
        pages = []
        url = "https://m.weibo.cn/api/container/getIndex"
        for since_id in itertools.count(1):
            params = {"containerid": f"231051_-_fans_-_{self.uid}"}
            if since_id != 1:
                params['since_id'] = since_id
            resp = self.download(url, params)
            if resp.json['ok'] == 0:  # 已到最后一页
                break
            pages.append(resp)
        return pages

    def on_save(self):
        self.logger.info("抓到粉丝列表", self.result)
