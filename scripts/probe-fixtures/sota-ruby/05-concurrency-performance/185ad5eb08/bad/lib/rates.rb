# frozen_string_literal: true

class Rates
  def self.table
    @table ||= load_table
  end
end
