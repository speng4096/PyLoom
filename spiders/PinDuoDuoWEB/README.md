## 拼多多爬虫网页版

#### 分类商品列表（ListTask）
搜索栏分类商品列表

| 字段                | 示例                                                         | 说明         |
| ------------------- | ------------------------------------------------------------ | ------------ |
| result.thumb_url    | https://t00img.yangkeduo.com/goods/images/2019-03-17/075bf350-0b66-4dfe-99e4-98eb912ac158.jpg | 商品图片链接 |
| result.country     |                                                    | 国度       |
| result.goods_name   | vivo原装耳机x21 x20...                                 | 商品名称     |
| result.short_name   | vivo原装耳机x21 x20...                                 | 商品简称    |
| result.sales_tip  | 已拼1490件                                 | 商品销售提示    |
| result.goods_id     | 6636323997                                                   | 商品id       |
| result.cnt          | 545                                                          | 已售数量     |
| result.normal_price | 2500                                                         | 商品售价     |
| result.market_price | 9900                                                         | 商品标价     |
| result.price        | 1280                                                         | 商品拼团价   |
| result.link_url        |  goods.html?goods_id=6636323997&gallery_id=103375816423         | 商品详情连接   |
| result.mall_name        |           | 商品店铺名称   |
| result.tag        |    ['极速退款']       | 商品标签   |
| result.updated_at   | 2018-09-02 13:58:08.176553                                   | 爬取时间     |

```python
self.result = [
    {
        'thumb_url': 'https://t00img.yangkeduo.com/goods/images/2019-03-17/075bf350-0b66-4dfe-99e4-98eb912ac158.jpg',
        'country': '', 
        'goods_name': 'vivo原装耳机x21 x20 x9 x7 x6 y67 y66 y37 y27线控带麦可通话',
        'short_name': 'vivo原装耳机x21 x20 x9 x7 x6 y67 y66 y37 y27线控带麦可通话',
        'sales_tip': '已拼1490件',
        'cnt': 1490,
        'goods_id': 6636323997,
        'hd_thumb_url': 'https://t00img.yangkeduo.com/goods/images/2019-03-17/075bf350-0b66-4dfe-99e4-98eb912ac158.jpg',
        'hd_url': '',
        'normal_price': 1480,
        'market_price': 9900,
        'price': 1280,
        'link_url': 'goods.html?goods_id=6636323997&gallery_id=103375816423',
        'mall_name': None,
        'tag': ['极速退款'],
        'updated_at': '2019-04-15 23:05:57.603136'
    },
    ...
]
```

### 商品详情（GoodsTask

```python
self.result = {
    'goods': {
        'serverTime': 1555340763,
        'serverTimeTen': 15553407630,
        'allowedRegions': '2,3,4,6,7,8,9,10,11,12,13,14,15,16,17,18,22,23,24,25,26,27,30,31,32',
        'catID': 5794,
        'country': '',
        'warehouse': '',
        'goodsDesc': '如果你还再为佩戴迷你型双耳容...',
        'goodsID': 2058994703,
        'goodsName': '防水超小无线蓝牙耳机双耳5.0跑步运动一对迷你vivo入耳oppo耳机',
        'shareDesc': '如果你还再为佩戴迷你型双耳容...',
        'goodsType': 1,
        'localGroups': [],
        'hasLocalGroup': 1,
        'bannerHeight': 375,
        'topGallery': [
            '//t00img.yangkeduo.com/goods/images/2019-02-21/3852f3ef-500c-4590-adf9-356a3397b0ce.jpg?imageMogr2/strip%7CimageView2/2/w/1300/q/80',
            ...
            ], 
        'viewImageData': [
            '//t00img.yangkeduo.com/goods/images/2019-02-21/3852f3ef-500c-4590-adf9-356a3397b0ce.jpg?imageMogr2/quality/70',
            ...
        ],
        'detailGallery': [
            {'url': '//t00img.yangkeduo.com/t09img/images/2018-07-03/84f1bc3741b3182df6f9d4dae633c9ec.jpeg?imageMogr2/quality/70', 'width': 790, 'height': 790}, 
            ...
        ], 
        'videoGallery': [], 
        'hasLiveGallery': False, 
        'descVideoGallery': [], 
        'mallID': 17984, 
        'groupTypes': [
            {'requireNum': '1', 'price': '0', 'totalPrice': '0', 'groupID': 2960548556, 'startTime': 1451577600, 'endTime': 2082729600, 'orderLimit': 999999},
            {'requireNum': '2', 'price': '0', 'totalPrice': '0', 'groupID': 2960548557, 'startTime': 1451577600, 'endTime': 2082729600, 'orderLimit': 999999}
        ], 
        'skus': [
            {
                'skuID': 38010790017,
                'quantity': 158,
                'initQuantity': 0,
                'isOnSale': 1,
                'soldQuantity': 0,
                'specs': [
                    {'spec_key': '颜色', 'spec_value': '黑色-支持双耳通话', 'spec_key_id': 1215, 'spec_value_id': 843019793}
                ],
                'thumbUrl': '//t00img.yangkeduo.com/t09img/images/2018-07-03/047554b0d2cd49183b5b2ed2380c528a.jpeg',
                'limitQuantity': 999999,
                'normalPrice': '218',
                'groupPrice': '162',
                'oldGroupPrice': '198',
                'skuExpansionPrice': '0',
                'unselectGroupPrice': '0'
            },
            ...
        ],
        'thumbUrl': '//t00img.yangkeduo.com/goods/images/2019-02-21/a5d77844f14e6438fe196b0d08fd9c63.jpeg',
        'hdThumbUrl': '//t00img.yangkeduo.com/goods/images/2019-02-21/7869f190bfd614a9d3151316f02642a1.jpeg', 
        'eventType': 0,
        'isOnSale': True,
        'isGoodsOnSale': True,
        'isSkuOnSale': True,
        'freeCoupon': [],
        'isApp': 0,
        'isFreshmanApp': 0,
        'sideSalesTip': '已拼47件',
        'bottomSalesTip': '',
        'hasAddress': False, 
        'catID1': 5752, 
        'catID2': 5793, 
        'catID3': 5794, 
        'catID4': 0, 
        'eventComing': False, 
        'isMutiGroup': False, 
        'isNewUserGroup': False,
        'isSpike': False,
        'isTodaySpike': False,
        'isTomorrowSpike': False, 
        'activity': {
            'activityID': 11464199, 
            'activityType': 101, 
            'startTime': 1554825600,
            'endTime': 1555775999
        },
        'isGroupFree': False,
        'isSpikeComing': False,
        'overseaType': 0,
        'isHaitao': False,
        'isAppNewerJoinGroup': False,
        'countryLogo': '',
        'gpv': None,
        'quickRefund': False,
        'rv': True,
        'maxNormalPrice': '218',
        'minNormalPrice': '218',
        'maxGroupPrice': '162',
        'minGroupPrice': '162',
        'maxOnSaleGroupPrice': '162',
        'minOnSaleGroupPrice': '162', 
        'maxOnSaleGroupPriceInCent': 16200, 
        'minOnSaleGroupPriceInCent': 16200, 
        'maxOnSaleNormalPrice': '218',
        'minOnSaleNormalPrice': '218', 
        'minTotalGroupPrice': '324', 
        'oldMinOnSaleGroupPriceInCent': 19800, 
        'unselectMinGroupPrice': '0', 
        'unselectMaxGroupPrice': '0', 
        'skipGoodsIDs': ['0'],
        'tag': -1,
        'icon': {'id': 5, 'url': 'http://t13img.yangkeduo.com/cart/2019-04-03/21bdb71af69e346fc73098a23e808656.png', 'width': 116, 'height': 45}, 
        'tagIcon': [], 
        'isSecondHand': 0, 
        'promotionBanner': {
            'id': 1, 
            'url': 'http://t13img.yangkeduo.com/cart/2019-04-03/77c14365ebf58c55a06f0e78fc017859.jpeg', 
            'default_url': 'http://t13img.yangkeduo.com/cart/2019-04-03/77c14365ebf58c55a06f0e78fc017859.jpeg', 
            'new_url': 'http://t13img.yangkeduo.com/cart/2019-04-03/77c14365ebf58c55a06f0e78fc017859.jpeg', 
            'url_v2': 'http://t13img.yangkeduo.com/cart/2019-04-03/77c14365ebf58c55a06f0e78fc017859.jpeg', 
            'url_v2_h': 96, 
            'url_v2_w': 750, 
            'serverTime': 1555340763
        }, 
        'isMallDsr': 1, 
        'hasPromotion': 1, 
        'appClientOnly': 0, 
        'isColdGoods': 1, 
        'singleCardStatus': 0, 
        'singleCardCount': 0, 
        'goodsProperty': [
            {'key': '佩戴方式', 'values': ['入耳式']},
            ...
        ],
        ...
    }
```

get_anticontent.js来自https://github.com/SergioJune/Spider-Crack-JS/blob/master/pinduoduo/get_anticontent.js