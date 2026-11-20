# frozen_string_literal: true

def self.search(q)
  where("name LIKE ?", "%#{sanitize_sql_like(q)}%")
end
