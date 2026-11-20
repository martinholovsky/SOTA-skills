# frozen_string_literal: true

def create
  cookies[:remember_token] = user.remember_token
end
