# frozen_string_literal: true

class User < ApplicationRecord
  validates :username, format: { with: /^[a-z0-9_]{3,32}$/ }
end
