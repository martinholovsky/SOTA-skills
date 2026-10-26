# frozen_string_literal: true

require "tempfile"

def export(user)
  Tempfile.create(["export", ".csv"]) { |f| f.write(user.to_csv_row) }
end
