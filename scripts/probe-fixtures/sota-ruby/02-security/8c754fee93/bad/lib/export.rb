# frozen_string_literal: true

def export(user)
  path = "/tmp/export-#{user.id}.csv"
  File.write(path, user.to_csv_row)
end
