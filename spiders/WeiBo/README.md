## 微博爬虫

### 用户信息（UserTask）

| 字段                     | 示例                               | 说明                               |
| ------------------------ | ---------------------------------- | ---------------------------------- |
| result.uid               | 1680938527                         | 用户唯一标识                       |
| result.screen_name       | 作恶太妖精                         | 用户昵称                           |
| result.statuses_count    | 12275                              | 微博数量                           |
| result.verified_type     | -1                                 | 账号类型，见[附录](#verified_type) |
| result.verified_type_ext | -1                                 | 附加账号类型，-1:无 1:橙V 0:金V    |
| result.description       | 因为追求梦想而伟大！梦想是熬出来的 | 简介                               |
| result.gender            | f                                  | 性别，f:女 m:男                    |
| result.mbtype            | 0                                  | 未知                               |
| result.urank             | 35                                 | 账号等级                           |
| result.mbrank            | 0                                  | 会员等级                           |
| result.followers_count   | 754                                | 粉丝数量                           |
| result.follow_count      | 602                                | 关注数量                           |
| result.profile_image_id  | 6431161fjw1e8qgp5bmzyj2050050aa8   | 头像图片号                         |
| result.status            | 0                                  | 账号状态，-1:不可用 0:可用         |
| result.updated_at        | 2018-08-10 00:02:02                | 抓取时间                           |

```python
self.result = {
    'uid': 2554193671, 
    'screen_name': '黑镜头世界', 
    'statuses_count': 88, 
    'verified_type': -1, 
    'verified_type_ext': -1, 
    'description': '一张残旧的老照片，能给你带来灌顶的震撼~', 
    'gender': 'm', 
    'mbtype': 0, 
    'urank': 2, 
    'mbrank': 0, 
    'followers_count': 84, 
    'follow_count': 4, 
    'profile_image_id': '983de707jw1e8qgp5bmzyj2050050aa8', 
    'status': 0, 
    'updated_at': datetime.datetime(2018, 8, 31, 0, 38, 10, 231390)
}
```



### 原创微博（UserTask）

每个用户前10条微博中的原创微博

| 字段                   | 示例                                 | 说明         |
| ---------------------- | ------------------------------------ | ------------ |
| result.mid             | 4264355334054790                     | 微博唯一标识 |
| result.uid             | 1225419417                           | 用户唯一标识 |
| result.text            | 哇！抽到了！爱国宝                   | 微博正文     |
| result.reposts_count   | 14                                   | 转发数量     |
| result.comments_count  | 114                                  | 评论数量     |
| result.attitudes_count | 1481                                 | 点赞数量     |
| result.source          | iPhone X                             | 来源         |
| result.updated_at      | 2018-08-10 00:02:09                  | 抓取时间     |
| result.created_at      | 2018-07-21 22:56:41                  | 发表时间     |
| result.images          | ["490a6a99gy1fthvjguf0gj20v91voqbr"] | 图片列表     |
| result.is_long_text    | False                                | 是否为长微博 |

```python
self.result = [
    {
        'mid': 4278823505781372,
        'uid': 2094949595,
        'text': '杭州的绿水青山留下了许多诗句，和风熏，杨柳轻，郁郁青山江水平，笑语满香径。什么使你爱上了这座城市?{网页链接}(https://weibo.com/tv/v/Gw6iL1Q0e?fid=1034:4276507087207862) \u200b',
        'reposts_count': 1,
        'comments_count': 1,
        'attitudes_count': 2,
        'source': '微博 weibo.com',
        'updated_at': datetime.datetime(2018, 8, 31, 0, 38, 11, 904636),
        'created_at': datetime.datetime(2018, 8, 30, 21, 8, 3, tzinfo=datetime.timezone(datetime.timedelta(0, 28800))),
        'images': [],
        'is_long_text': False
    },
    {
        'mid': 4278785248875113,
        'uid': 2094949595,
        'text': '你当时学的专业是什么？你现在又在做什么工作呢？ \u200b',
        'reposts_count': 0,
        'comments_count': 12,
        'attitudes_count': 1,
        'source': '微博 weibo.com',
        'updated_at': datetime.datetime(2018, 8, 31, 0, 38, 11, 904846),
        'created_at': datetime.datetime(2018, 8, 30, 18, 36, 3, tzinfo=datetime.timezone(datetime.timedelta(0, 28800))),
        'images': ['7cde64dbgy1furl2c240jj20e80cujs2'],
        'is_long_text': False
    },
]

```



### 转发微博（UserTask）

每个用户前10条微博中的转发微博

| 字段                   | 示例                   | 说明                            |
| ---------------------- | ---------------------- | ------------------------------- |
| result.mid             | 4269756171586532       | 微博唯一标识                    |
| result.uid             | 1680938527             | 用户唯一标识                    |
| result.text            | //@李宇春如初:转发微博 | 微博正文                        |
| result.reposts_count   | 0                      | 转发数量                        |
| result.comments_count  | 0                      | 评论数量                        |
| result.attitudes_count | 0                      | 点赞数量                        |
| result.source          | iPhone客户端           | 来源                            |
| result.pmid            | 4269752379437757       | 父级微博的mid（上层转发，可空） |
| result.smid            | 4269748974496983       | 源微博的mid（原创微博）         |
| result.suid            | 5427461387             | 源微博的uid                     |
| result.updated_at      | 2018-08-10 00:02:02    | 抓取时间                        |
| result.created_at      | 2018-08-05 20:37:42    | 发表时间                        |

```python
self.result = [
    {'mid': 4278871820165470,
     'uid': 1802393212,
     'text': '这壁纸超萌哦，喜欢就快来打call @Line壁纸酱',
     'reposts_count': 0,
     'comments_count': 0,
     'attitudes_count': 2,
     'source': '皮皮时光机',
     'updated_at': datetime.datetime(2018, 8, 31, 0, 38, 12, 250057),
     'created_at': datetime.datetime(2018, 8, 31, 0, 20, 2, tzinfo=datetime.timezone(datetime.timedelta(0, 28800))),
     'pmid': 0,
     'smid': 4278723350035431,
     'suid': 6150916523
     },
    {
        'mid': 4278866795185761,
        'uid': 1802393212,
        'text': '[心]',
        'reposts_count': 0,
        'comments_count': 0,
        'attitudes_count': 2,
        'source': '皮皮时光机',
        'updated_at': datetime.datetime(2018, 8, 31, 0, 38, 12, 250450),
        'created_at': datetime.datetime(2018, 8, 31, 0, 0, 4, tzinfo=datetime.timezone(datetime.timedelta(0, 28800))),
        'pmid': 0,
        'smid': 4266013078506248,
        'suid': 5604000425}
]
```



### 关注列表（FollowerTask）

每个用户最后180个关注、部分大V关注

| 字段   | 示例                     | 说明                    |
| ------ | ------------------------ | ----------------------- |
| result | [5427461387, 1680938527] | 关注列表中所有用户的uid |

```python
self.result = [
    1199430302, 5291824241, 1744583555, 1225627080, 1192504311, 1539469391, 1831216671, 1855790127,
]
```

+ 通过self.uid获取当前用户UID



### 粉丝列表（FanTask）

每个用户最后4500个粉丝、部分大V粉丝

| 字段   | 示例                       | 说明                    |
| ------ | -------------------------- | ----------------------- |
| result | [5427461387", "1680938527] | 粉丝列表中所有用户的uid |

```python
self.result = [
    2011541160, 6561198332, 5650361179, 5203386014, 6586203686, 3975892466, 5280555723, 6200526771,
]
```

+ 通过self.uid获取当前用户UID



### 附录

#### verified_type

|值|含义|
|:---|:---|
|-1|无认证|
|0|个人认证|
|1|政府|
|2|企业|
|3|媒体|
|4|校园|
|5|网站|
|6|应用|
|7|机构|
|8|待审企业|
|200|初级达人|
|220|中高级达人|
|400|已故V用户|

