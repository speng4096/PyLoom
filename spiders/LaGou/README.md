## 拉钩爬虫

### 职位详情（JobDetails）

| 字段               | 示例                                         | 说明                  |
| ------------------ | -------------------------------------------- | --------------------- |
| result._id         | 5080106                                      | 职位id                |
| result.title       | 演员实习生                                   | 名称                  |
| result.label       | ['移动互联网', '广告营销']                   | 标签                  |
| result.job_request | 2k-4k/上海 /经验应届毕业生 /大专及以上 /实习 | 要求                  |
| result.advantage   | 周末双休,地铁周边,做五休二,氛围融洽          | 职位诱惑              |
| result.job_bt      | 职位描述：岗位职责：1参与公司广告...         | 职位描述              |
| result.work_addr   | 上海-徐汇区- 桂林路396号3号楼                | 工作地址              |
| result.status      | 0                                            | 状态，0:进行中 1:结束 |
| result.job_company | 乐推（上海）文化传播有限公司                 | 公司名字              |
| result.type        | 移动互联网,广告营销领域                      | 类型                  |
| result.time        | 2018-09-02                                   | 发布时间              |

```python
self.result = {
    '_id': '5080106',
    'title': '演员实习生', 
    'label': ['移动互联网', '广告营销'],
    'job_request': '2k-4k/上海 /经验应届毕业生 /大专及以上 /实习',
    'advantage': '周末双休,地铁周边,做五休二,氛围融洽', 
    'job_bt': '职位描述：岗位职责：1参与公司广告和短剧的拍摄；2负责公司项目前期筹备等的相关工作；3出演抖音广告与搞笑视频。任职要求：1长相甜美，外形清新亮丽，镜头感强，有强烈的表现力；2专科以上学历，表演系专业优先；3性格活泼开朗、思维活跃、为人正直；4工作态度积极；5仅仅招收女演员。',
    'work_addr': '上海-徐汇区- 桂林路396号3号楼', 
    'status': 0, 
    'job_company': '乐推（上海）文化传播有限公司', 
    'type': '移动互联网,广告营销领域', 
    'time': '2018-09-02'
}
```



### 公司详情（GongSiDetails）

| 字段                     | 示例                       | 说明     |
| ------------------------ | -------------------------- | -------- |
| result._id               | 324                        | 公司id   |
| result.company_abbr      | 爱立示                     | 简称     |
| result.company_full_name | 慈溪爱立示信息科技有限公司 | 全称     |
| result.type              | 信息安全,数据服务          | 类型     |
| result.process           | 未融资                     | 融资状态 |
| result.number            | 15-50人                    | 人数     |
| result.address           | 北京                       | 公司地点 |
| result.label             | ['技能培训', '岗位晋升']   | 公司标签 |
| result.website           | http://www.alstru.com      | 公司网站 |

```python
self.result = {
    '_id': '324', 
    'company_abbr': '爱立示',
    'company_full_name': '慈溪爱立示信息科技有限公司',
    'type': '信息安全,数据服务',
    'process': '未融资', 
    'number': '15-50人',
    'address': '北京',
    'label': ['技能培训', '岗位晋升', '扁平管理', '领导好', '五险一金', '弹性工作'],
    'website': 'http://www.alstru.com'
}
```

