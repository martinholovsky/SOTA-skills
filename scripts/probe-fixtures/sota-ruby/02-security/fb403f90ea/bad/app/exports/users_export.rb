require "csv"

class UsersExport
  def call(users)
    CSV.generate do |csv|
      users.each { |u| csv << [u.name, u.email] }
    end
  end
end
