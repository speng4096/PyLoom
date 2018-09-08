## 自如爬虫

### 安装

1. [安装tesseract-ocr](https://github.com/tesseract-ocr/tesseract/wiki)

2. 安装pytesseract库

   ```
   pip install pytesseract
   ```


### 房源列表(NLTask)

房源列表中的房源信息

| 字段             | 示例                                                  | 说明         |
| ---------------- | ----------------------------------------------------- | ------------ |
| result.price     | 1160                                                  | 价格         |
| result.href      | www.ziroom.com/z/vr/61441027.html                     | 详情信息链接 |
| result.img_src   | static8.ziroom.com/phoenix/pc/images/list/loading.jpg | 图片         |
| result.block     | 天恒乐活城                                            | 小区名       |
| result.name      | 整租 · 天恒乐活城2居室-南                             | 房源名       |
| result.site      | [通州通州其它] 亦庄线次渠南                           | 位置         |
| result.detail    | 14.1 ㎡\|6/6层\|3室1厅距15号线石门站690米             | 细节         |
| result.room_tags | ['离地铁近', '独立阳台', '集体供暖', '友家3.0 木棉']  | 标签         |

```python
self.result = [
    {
	'price': '1830', 
     	'href': 'www.ziroom.com/z/vr/61514855.html',
     	'img_src': 'static8.ziroom.com/phoenix/pc/images/list/loading.jpg',
     	'block': '世茂维拉', 'name': '友家 · 世茂维拉5居室-南卧',
     	'site': '[房山长阳] 房山线广阳城',
     	'detail': '12.3 ㎡|5/5层|5室1厅距房山线广阳城站696米有2间空房',
     	'room_tags': ['离地铁近', '独卫', '集体供暖', '友家4.0 拿铁']
    }, 
    {
	'price': '1830',
     	'href': 'www.ziroom.com/z/vr/261810.html',
     	'img_src': 'static8.ziroom.com/phoenix/pc/images/list/loading.jpg',
     	'block': '前进花园石门苑',
     	'name': '友家 · 前进花园石门苑3居室-南卧',
     	'site': '[顺义顺义城] 15号线石门',
     	'detail': '14.1 ㎡|6/6层|3室1厅距15号线石门站690米',
     	'room_tags': ['离地铁近', '独立阳台', '集体供暖', '友家4.0 布丁']
    },
    ...
]
```



### 房源详情(VRTask)

| 字段                     | 示例                                                     | 说明                                       |
| ------------------------ | -------------------------------------------------------- | ------------------------------------------ |
| result.img               | ['http://pic.ziroom.com/house_images.jpg',...]           | 介绍图片                                   |
| result.room_name         | 和平家园小区4居室-02卧                                   | 名称                                       |
| result.ellipsis          | [昌平 沙河] 昌平线 昌平                                  | 位置                                       |
| result.room_id           | 61264525                                                 | 房间id                                     |
| result.house_id          | 60203175                                                 | 房屋id                                     |
| result.current_city_code | 110000                                                   | 所在城市编码，见[附录](#current_city_code) |
| result.detail_room       | {'面积': '15.4㎡', '朝向': '南', '户型': '4室1厅合',...} | 房屋参数                                   |
| result.number            | BJZRGY0818215849_02                                      | 编号                                       |
| result.periphery         | 学校：中国政法大学法学院、中国石油大学...                | 周边                                       |
| result.traffic           | 公交：314路、昌平9路...                                  | 交通                                       |
| result.configuration     | ['bed', 'desk', 'chest', 'calorifier']                   | 配置                                       |
| result.roommate          | [{性别': 'man', '房间号': '01卧', '星座': '天蝎座',...}] | 室友信息                                   |
| result.price             | 1890                                                     | 价格                                       |

```python
self.result = {
    'img':[
	'http://pic.ziroom.com/house_images/g2m1/M00/5B/DF/v180x135.jpg',
	'http://pic.ziroom.com/house_images/g2m1/M00/5D/0B/v180x135.jpg'
    ],
    'room_name': '和平家园小区4居室-02卧', 
    'ellipsis': '[昌平 沙河] 昌平线 昌平', 
    'room_id': '61264525', 
    'house_id': '60203175',
    'current_city_code': '110000',
    'detail_room': {
        '面积': '15.4㎡',
        '朝向': '南',
        '户型': '4室1厅合',
        '楼层': '6/6层',
	'交通': '距15号线石门307米距15号线顺义1621米距15号线南法信2290米'
    }, 
    'number': 'BJZRGY0818215849_02', 
    'periphery': '学校：中国政法大学法学院 医院：北京化工大学校医院',
    'traffic': '公交：314路、昌平9路、914路、昌平3路、昌平5路、326路、345路', 
    'configuration': ['bed', 'desk', 'chest', 'calorifier], 
    'roommate':[
        { 
	    '性别': 'man',
            '房间号': '01卧',
            '星座': '天蝎座',
            '职业': '产品',
            '入住时间': '2018/07-2019/07'
        },
        {
            '性别': 'current',
            '房间号': '02卧',
            '星座': '…',
            '职业': '…',
            '入住时间': '…'
        }
    ], 
    'price': 1890
}
```

+ 房间室友（result.roommate）不存在时，性别为current，'…'代表信息为空

### 附录

#### current_city_code

| 城市编码 | 城市名称 |
| -------- | -------- |
| 110000   | 北京     |
| 310000   | 上海     |
| 440300   | 深圳     |
| 330100   | 杭州     |
| 320100   | 南京     |
| 440100   | 广州     |
| 510100   | 成都     |
| 420100   | 武汉     |
| 120000   | 天津     |

