## 豆瓣图书爬虫

### 图书信息（BookDetailsTask）

| 字段                 | 示例                                                         | 说明     |
| -------------------- | ------------------------------------------------------------ | -------- |
| result.title         | 社会研究方法                                                 | 书名     |
| result.cover         | https://img3.doubanio.com/view/subject/l/public/s2932505.jpg | 封面     |
| result.info          | {'作者': '[美]劳伦斯·纽曼', '出版社', '中国人民大学出版社'}  | 基本信息 |
| result.rating_num    | 9.0                                                          | 评分     |
| result.rating_people | 202                                                          | 评分人数 |
| result.intro         | 迄今所见中文社会研究方法书中最好的……                         | 简介     |
| result.tags          | ['社会学', '研究方法']                                       | 标签     |

```python
self.result = {
    'title': '社会研究方法', 
    'cover': 'https://img3.doubanio.com/view/subject/l/public/s2932505.jpg', 
    'info': {
        '作者': '[美]劳伦斯·纽曼', 
        '出版社': '中国人民大学出版社', 
        '副标题': '定性和定量的取向', 
        '原作名': 'Basics of Social Research: Qualitative and Quantitative Approaches', 
        '译者': '郝大海', 
        '出版年': '2007', 
        '页数': '809', 
        '定价': '89.80元', 
        '丛书': '社会学译丛·经典教材系列', 
        'ISBN': '9787300075648'
    }, 
    'rating_num': '9.0', 
    'rating_people': '202', 
    'intro': '迄今所见中文社会研究方法书中最好的一本，极力推荐研究生教学中采用。理清了许多问题，对定性和定量的对比非常精彩。', 
    'tags': ['社会学', '研究方法', '方法论', '社会研究方法', '定性', '教材', '纽曼', '定量']
}
```

+ 基本信息（result.info），每本书的字段不固定。

