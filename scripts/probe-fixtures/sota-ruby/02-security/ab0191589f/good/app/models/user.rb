# frozen_string_literal: true

class User < ApplicationRecord
  validates :username, format: { with: /\A[a-z0-9_]{3,32}\z/ }
end
