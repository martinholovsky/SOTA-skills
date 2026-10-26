# frozen_string_literal: true

class ReportWriter
  def write(path, rows)
    File.open(path, "w") do |file|
      rows.each { |r| file.puts(r.join(",")) }
    end
  end
end
