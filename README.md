# PyLoom，爬龙！

PyLoom想为有价值的网站编写爬虫，让开发者便捷地获取结构化的数据。

PyLoom由三个部分组成，

1. 框架，减少编写、运行、维护爬虫的工作量。

2. 爬虫，寻找有价值的目标为其开发爬虫，并维护既有爬虫的可用性。

   预期19年底，PyLoom将拥有围绕电子商务、房屋租售、社交网络、新闻媒体的数十个爬虫。

3. 升级爬虫，对于频繁使用的爬虫，增强其能力
   + 增强定制能力，例如支持限定地区、类别、关键字抓取；
   + 增强抓取策略，减少对代理、打码接口的使用；
   + 增强更新策略，更细粒度地计算重复抓取的时间。

目前进度，

①部分完成，开发常见爬虫够用了，随爬虫的开发迭代出更多功能；

②已有几款爬虫，放置于`spiders`目录。



## 安装

1. **环境要求**

   + python 3.6.0+
   + redis 2.6+
   + 类unix系统

2. **安装PyLoom**

   ```bash
   git clone https://github.com/spencer404/PyLoom.git
   python3.6 -m pip install -e ./PyLoom
   ```

   > 添加 `-i https://pypi.douban.com/simple` 参数，利用豆瓣镜像提速。

   >出现错误`fatal error: Python.h: No such file or directory`时，
   >
   >需安装对应平台的python3.x-devel包
   >



## 运行

以运行`spiders/WeiBo`为例，

1. **最简参数启动爬虫**

   ```bash
   pyloom run -s PyLoom/spiders/WeiBo
   ```

   >在爬虫目录中执行`run`时，可省略`-s`参数。

2. **启动代理池**

   ```bash
   pyloom proxy run
   ```

3. **添加代理**

   根据命令提示，添加名为"xxx"的代理

   ```bash
   pyloom proxy add
   ```

4. **使用代理启动爬虫**

   ```bash
   pyloom run --proxy xxx
   ```

   命令`run`的部分常用参数：

   ```bash
   -l, --level    日志级别
   -s, --spider   指定爬虫目录
   -r, --redis    指定redis地址(URL形式)
   -C, --clear    清空队列、代理数据后运行
   --proxy        使用指定代理运行，逗号分隔多个代理
   --damon        作为守护进程运行
   -p             子进程数量
   -t             每个子进程的线程数量
   ```

   在多台服务器上运行时，若参数`-s、-r`所指向的目标相同，即可横向扩容性能。

   默认地，PyLoom将抓到数据打印在日志中，你可以修改`on_save`函数自定义如何保存。