# 爬虫初始化时填入队列的种子页面
seeders = [
    "https://book.douban.com/tag/?view=cloud"
]
# 调度间隔时间（秒）
# 控制当前爬虫的抓取频率
interval = -10
# 任务超时时间（秒）
# 超时后，将被移入tag='timeout'的异常队列中
timeout = 120
# 设置BloomFilter精度，用于过滤'已完成'的URL，避免重复抓取
# 若精度设置过低，会造成过多的页面被误报为'已完成'
# 应权衡爬虫对误报的忍耐度与服务器内存消耗，酌情更改
# 特别注意，此字段一经设置不可更改
precision = 0.0001
# 自定义参数
# Task中使用self.args访问这里的args
args = {}
