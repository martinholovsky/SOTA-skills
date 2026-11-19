# frozen_string_literal: true

class Proxy
  def method_missing(name, *args)
    target.public_send(name, *args)
  end
end
