# frozen_string_literal: true

def password=(plain)
  self.password_hash = BCrypt::Password.create(plain)
end
