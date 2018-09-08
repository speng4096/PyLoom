-- 将一组URLs排重后添加至队列
-- Keys: name priority
-- Argv: url [url ...]
-- Return: count，成功数量（不重复数量）

local bloom_check = function(name, entries, precision, value)
    local prefix = "queue:" .. name .. ":filter:bloom"
    local count = redis.call('GET', prefix .. ':count')
    if not count then
        return 0
    end

    local factor = math.ceil((entries + count) / entries)
    -- 0.69314718055995 = ln(2)
    local index = math.ceil(math.log(factor) / 0.69314718055995)
    local scale = math.pow(2, index - 1) * entries
    local hash = redis.sha1hex(value)

    -- This uses a variation on:
    -- 'Less Hashing, Same Performance: Building a Better Bloom Filter'
    -- https://www.eecs.harvard.edu/~michaelm/postscripts/tr-02-05.pdf
    local h = {}
    h[0] = tonumber(string.sub(hash, 1, 8), 16)
    h[1] = tonumber(string.sub(hash, 9, 16), 16)
    h[2] = tonumber(string.sub(hash, 17, 24), 16)
    h[3] = tonumber(string.sub(hash, 25, 32), 16)

    -- Based on the math from: http://en.wikipedia.org/wiki/Bloom_filter#Probability_of_false_positives
    -- Combined with: http://www.sciencedirect.com/science/article/pii/S0020019006003127
    -- 0.4804530139182 = ln(2)^2
    local maxbits = math.floor((scale * math.log(precision * math.pow(0.5, index))) / -0.4804530139182)
    -- 0.69314718055995 = ln(2)
    local maxk = math.floor(0.69314718055995 * maxbits / scale)
    local b = {}

    for i = 1, maxk do
        table.insert(b, h[i % 2] + i * h[2 + (((i + (i % 2)) % 4) / 2)])
    end

    for n = 1, index do
        local key = prefix .. ':' .. n
        local found = true
        local scalen = math.pow(2, n - 1) * entries

        -- 0.4804530139182 = ln(2)^2
        local bits = math.floor((scalen * math.log(precision * math.pow(0.5, n))) / -0.4804530139182)

        -- 0.69314718055995 = ln(2)
        local k = math.floor(0.69314718055995 * bits / scalen)

        for i = 1, k do
            if redis.call('GETBIT', key, b[i] % bits) == 0 then
                found = false
                break
            end
        end

        if found then
            return 1
        end
    end

    return 0
end

local name = KEYS[1]
local priority = KEYS[2]
local key_spider = "spider:" .. name
local key_waiting = "queue:" .. name .. ":waiting:" .. priority
local key_filter_queue = "queue:" .. name .. ":filter:queue"
local filter = {} -- 对ARGV排重
local urls = {} -- 将被批量添加到waiting队列的URL

-- 从爬虫配置中读取布隆参数
local precision = redis.call('HGET', key_spider, 'precision')
if not precision then
    return { err = "爬虫未配置'precision'" }
end

-- 排重
for i = 1, #ARGV do
    local url = ARGV[i]
    local exists = filter[url] or
            bloom_check(name, 1000000, precision, url) == 1 or
            redis.call('SISMEMBER', key_filter_queue, url) == 1
    if not exists then
        filter[url] = true
        table.insert(urls, url)
    end
end

-- 加入队列
if #urls == 0 then
    return 0
else
    redis.call('LPUSH', key_waiting, unpack(urls))
    redis.call('SADD', key_filter_queue, unpack(urls))
    return #urls
end
