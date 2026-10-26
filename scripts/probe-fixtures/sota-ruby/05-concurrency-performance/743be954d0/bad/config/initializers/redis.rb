# frozen_string_literal: true

REDIS = Redis.new(url: ENV.fetch("REDIS_URL"))
