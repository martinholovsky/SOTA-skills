# frozen_string_literal: true

require "sidekiq/web"

Sidekiq::Web.use Rack::Auth::Basic do |user, password|
  ActiveSupport::SecurityUtils.secure_compare(user, ENV.fetch("SIDEKIQ_USER")) &
    ActiveSupport::SecurityUtils.secure_compare(password, ENV.fetch("SIDEKIQ_PASSWORD"))
end
