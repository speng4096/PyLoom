## 拼多多爬虫

#### 分类商品列表（OperationTask）

搜索栏分类商品列表

| 字段                | 示例                                                         | 说明         |
| ------------------- | ------------------------------------------------------------ | ------------ |
| result.goods_id     | 2721076214                                                   | 商品id       |
| result.goods_name   | 【两件装】秋季男装长袖t恤...                                 | 商品名称     |
| result.thumb_url    | http://t00img.yangkeduo.com/goods/images/2018-09-01/75ed6981d7961404ba75f0b1f9dd6322.jpeg | 商品图片链接 |
| result.cnt          | 545                                                          | 已售数量     |
| result.normal_price | 2500                                                         | 商品售价     |
| result.market_price | 9900                                                         | 商品标价     |
| result.price        | 1280                                                         | 商品拼团价   |
| result.updated_at   | 2018-09-02 13:58:08.176553                                   | 爬取时间     |

```python
self.result = [
    {
        'goods_id': 2721076214,
        'goods_name': '【两件装】秋季男装长袖t恤青年韩版潮流上衣学生修身百搭打底衫',
        'thumb_url': 'http://t00img.yangkeduo.com/goods/images/2018-09-01/75ed6981d7961404ba75f0b1f9dd6322.jpeg',
        'cnt': 545,
        'normal_price': 2500,
        'market_price': 9900,
        'price': 1280,
        'updated_at': '2018-09-02 13:58:08.176553'
    },
    {
        'goods_id': 142150779,
        'goods_name': '【花花公子贵宾】春夏秋款宽松直筒牛仔裤男弹力休闲商务大码长裤',
        'thumb_url': 'http://t00img.yangkeduo.com/goods/images/2018-08-14/a18025b1e91445e5ac2acb26be773cd1.jpeg',
        'cnt': 294167,
        'normal_price': 4990,
        'market_price': 29800,
        'price': 2990,
        'updated_at': '2018-09-02 13:58:08.176553'
    }
    ...
]
```



#### 商品详情（GoodsTask）

| 字段                | 示例                                 | 说明                         |
| ------------------- | ------------------------------------ | ---------------------------- |
| result.goods_sn     | "1805231480604761"                   | sn码                         |
| result.goods_id     | 1480604761                           | 商品id                       |
| result.cat_id       | 9813                                 | 搜索id                       |
| result.goods_name   | 【凡爱宝贝】3d立体墙贴自粘...        | 名称                         |
| result.goods_desc   | 【3d立体墙贴】【环保无味】...        | 简介                         |
| result.market_price | 3500                                 | 标价                         |
| result.is_onsale    | 1                                    | 是否在售，0:下架 1:出售      |
| result.thumb_url    | http://t00img.yangkeduo.com/...      | 商品图标                     |
| result.hd_thumb_url | http://t00img.yangkeduo.com/...      | 商品放大图标                 |
| result.image_url    | http://t00img.yangkeduo.com/...      | 商品图片链接                 |
| result.price        | {"min_on_sale_group_price": 358,...} | 商品价格,见[详情](#price)    |
| result.gallery      | [{"id": 34954263707,'url':...}]      | 商品详情介绍                 |
| result.created_at   | 1527069514                           | 创建时间戳                   |
| result.sales        | 167701                               | 销售量                       |
| result.cat_id_list  | [9316, 9402, 9813]                   | 商品多级分类                 |
| result.sku          | [{"sku_id": 33940681934,...}]        | 商品规格详情，见[详情](#sku) |

```python
self.result = {
    "goods_sn": "1805231480604761", 
    "goods_id": 1480604761, 
    "cat_id": 9813, 
    "goods_name": "【凡爱宝贝】3d立体墙贴自粘防水墙纸防撞壁纸客厅卧室砖纹贴纸", 
    "goods_desc": "【3d立体墙贴】【环保无味】【无甲醛 免胶自粘】绿色环保、无毒、无味,免人工,带胶撕开底纸即可粘贴,产品粘性强,不易脱落,具有很好的防撞、防水、防潮效果,易遮盖污点,环保无异味,施工简单,规格:70cm宽X77cm高; 工厂直销,砖纹形,装饰儿童房、卧室、客厅背景墙、走廊,也可发挥想象自由裁剪DIY。【计算方式】长x宽=面积,总面积÷单片面积=片数,一片尺寸是70cm宽X77cm高=0.539平方【友情提示】为避免不够,建议需要尽量多买2片备着,因为不同批次颜色有可能存在差异,所以请亲们一次购买足够。", 
    "market_price": 3500, 
    "is_onsale": 1, 
    "thumb_url": "http://t00img.yangkeduo.com/goods/images/2018-08-20/f9ba2f52be83d2f55142c55f44ec678c.jpeg", 
    "hd_thumb_url": "http://t00img.yangkeduo.com/goods/images/2018-08-20/8c5790dfea2422328ee3a487f3685ed6.jpeg", 
    "image_url": "http://t00img.yangkeduo.com/goods/images/2018-07-22/95065d45399fce770bb49de0fba5c590.jpeg", 
    "goods_type": 1, 
    "gallery": [
        {
            "id": 34954263707, 
            "url": "http://t00img.yangkeduo.com/t10img/images/2018-07-16/d864ed35818e90521cf858951d9dc349.jpeg"
        }
    ], 
    "created_at": 1527069514, 
    "sales": 167701, 
    "price": {
        "min_on_sale_group_price": 358, 
        "max_on_sale_group_price": 781, 
        "min_on_sale_normal_price": 490, 
        "max_on_sale_normal_price": 1500, 
        "min_group_price": 358, 
        "max_group_price": 781, 
        "max_normal_price": 1500, 
        "min_normal_price": 490, 
        "old_min_on_sale_group_price": 390, 
        "old_max_on_sale_group_price": 860, 
        "old_min_group_price": 390, 
        "old_max_group_price": 860
    }, 
    "cat_id_list": [9316, 9402, 9813], 
    "sku": [
        {
            "sku_id": 33940681934, 
            "goods_id": 1480604761, 
            "thumb_url": "http://t00img.yangkeduo.com/t07img/images/2018-07-12/94b7c9302b62c64e22914e6e36fb9d40.png", 
            "quantity": 0, 
            "normal_price": 1500, 
            "group_price": 561, 
            "old_group_price": 610, 
            "specs": [
                {
                    "spec_key": "尺寸", 
                    "spec_value": "尺寸70*77厘米/1张"
                }, 
                {
                    "spec_key": "颜色", 
                    "spec_value": "特价白色（70*77厘米）"
                }
            ]
        }
    ]
}
```

+ cat_id_list为商品的多级分类栏id，依次为商品一级分类、商品二级分类、商品三级分类

### 附录

#### price

| 值                          | 含义                   |
| --------------------------- | ---------------------- |
| min_on_sale_group_price     | 在售商品团购最低价     |
| max_on_sale_group_price     | 在售商品团购最高价     |
| min_on_sale_normal_price    | 在售商品最低价         |
| max_on_sale_normal_price    | 在售商品最高价         |
| min_group_price             | 商品团购最低价         |
| max_group_price             | 商品团购最高价         |
| max_normal_price            | 商品最高价             |
| min_normal_price            | 商品最低价             |
| old_min_on_sale_group_price | 在售商品团购旧的最低价 |
| old_max_on_sale_group_price | 在售商品团购旧的最高价 |
| old_min_group_price         | 商品团购旧的最低价     |
| old_max_group_price         | 商品团购旧的最高价     |

#### sku

| 值               | 含义         |
| ---------------- | ------------ |
| sku_id           | 规格id       |
| goods_id         | 商品id       |
| thumb_url        | 规格图片链接 |
| quantity         | 数据         |
| normal_price     | 标价         |
| group_price      | 团购价       |
| old_group_price  | 旧的团购价   |
| specs.spec_key   | 规格参数     |
| specs.spec_value | 规格参数值   |

