require "json"

class UsersExport
  def call(users)
    JSON.generate(users.map { |u| { name: u.name, email: u.email } })
  end
end
