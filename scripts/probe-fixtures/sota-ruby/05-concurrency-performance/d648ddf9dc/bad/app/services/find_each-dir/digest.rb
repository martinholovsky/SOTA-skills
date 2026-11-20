# frozen_string_literal: true

def send_all
  User.where(active: true).each { |u| DigestMailer.weekly(u).deliver_later }
end
