# frozen_string_literal: true

REDIS = ConnectionPool.new(size: 5) { Redis.new(url: ENV.fetch("REDIS_URL")) }
