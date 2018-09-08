-- 请求分配任务
-- Keys: now
-- Argv: name [name ...]
-- Return: (url, name, address)
local now = tonumber(KEYS[1])
for i = 1, #ARGV do
    local name = ARGV[i] -- 爬虫名
    local key_spider = "spider:" .. name
    local status = tonumber(redis.call("HGET", key_spider, "status"))
    redis.call("HSET", key_spider, "last_heartbeat_time", now)
    -- 条件: 爬虫状态至少为就绪态
    if status >= 10 then
        local interval = cjson.decode(redis.call("HGET", key_spider, "interval"))
        local last_pop_time = cjson.decode(redis.call("HGET", key_spider, "last_pop_time"))
        -- 条件: 爬虫已到可用时间
        if now >= last_pop_time + interval then
            local proxies = cjson.decode(redis.call("HGET", key_spider, "proxies"))
            local address = false
            -- 爬虫被设置了代理，把代理池弹空也要弹出一个可用代理
            if #proxies ~= 0 then
                local recycle = {}
                while not address do
                    address = redis.call("RPOP", "proxy:addresses:" .. name)
                    -- 代理池空了，不再继续弹出
                    if not address then
                        break
                    end
                    local t1 = string.find(address, ":", 1)
                    local t2 = string.find(address, ":", t1 + 1)
                    local valid_at = tonumber(string.sub(address, 1, t1 - 1))
                    local expire_at = tonumber(string.sub(address, t1 + 1, t2 - 1))

                    if valid_at > now then
                        -- 代理未到可用时间，放回去 -> 重新弹出
                        table.insert(recycle, address)
                        address = false
                    else
                        -- 代理已到可用时间，并未过期 -> 已拿到代理！
                        if expire_at > now then
                            break
                        end
                        -- 代理已到可用时间，已过期 -> 重新弹出
                        -- 过期代理不归还
                    end
                end
                if #recycle ~= 0 then
                    redis.call("LPUSH", "proxy:addresses:" .. name, unpack(recycle))
                end
            end
            -- 条件: 爬虫未设置代理或代理池中可用代理不全为空
            if #proxies == 0 or address then
                local key_processing = "queue:" .. name .. ":processing"
                for priority = 0, 4 do
                    -- 条件: 爬虫名下所有队列不全为空
                    local key_waiting = "queue:" .. name .. ":waiting:" .. priority
                    local url = redis.call("RPOP", key_waiting)
                    -- 已满足所有条件，发布任务
                    if url then
                        -- 加入processing
                        redis.call("HSET", key_processing, url, now)
                        -- 更新last_pop_time
                        redis.call("HSET", key_spider, "last_pop_time", now)
                        return { url, name, address }
                    end
                end
                -- 队列全部为空时，设置爬虫状态为已完成
                local processing_len = redis.call("HLEN", key_processing)
                if processing_len == 0 then
                    redis.call("HSET", key_spider, "status", 0)
                end
            end
        end
    end
end

return { false, false, false }
