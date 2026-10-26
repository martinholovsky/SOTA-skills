# frozen_string_literal: true

class ReportWriter
  def write(path, rows)
    file = File.open(path, "w")
    rows.each { |r| file.puts(r.join(",")) }
  end
end
