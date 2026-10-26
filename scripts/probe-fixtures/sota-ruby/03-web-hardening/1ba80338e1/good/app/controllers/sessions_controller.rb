# frozen_string_literal: true

def create
  cookies.signed[:remember_token] = { value: user.remember_token, httponly: true, secure: true, same_site: :lax }
end
