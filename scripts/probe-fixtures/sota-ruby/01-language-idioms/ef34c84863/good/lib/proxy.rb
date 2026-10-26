# frozen_string_literal: true

class Proxy
  def method_missing(name, *args)
    target.respond_to?(name) ? target.public_send(name, *args) : super
  end

  def respond_to_missing?(name, include_private = false)
    target.respond_to?(name, include_private) || super
  end
end
