# frozen_string_literal: true

def password=(plain)
  self.password_hash = Digest::SHA256.hexdigest(plain + salt)
end
