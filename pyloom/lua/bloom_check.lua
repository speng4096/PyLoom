--[[
The MIT License (MIT)

Copyright (c) 2017 Erik Dubbelboer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
]]

-- 在原作者Erik Dubbelboer的成果上做了简单修改
-- https://github.com/erikdubbelboer/redis-lua-scaling-bloom-filter

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

-- 从爬虫配置中读取布隆参数
local name = KEYS[1]
local key_spider = "spider:" .. name
local precision = redis.call('HGET', key_spider, 'precision')
if not precision then
    return { err = "爬虫未配置'precision'" }
end

return bloom_check(name, 1000000, precision, ARGV[1])
