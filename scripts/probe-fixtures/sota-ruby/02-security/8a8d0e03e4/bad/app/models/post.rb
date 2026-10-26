# frozen_string_literal: true

def self.sorted(col)
  order(Arel.sql("#{col} DESC"))
end
