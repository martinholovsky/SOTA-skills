# frozen_string_literal: true

def self.search(q)
  where("name LIKE ?", "%#{q}%")
end
