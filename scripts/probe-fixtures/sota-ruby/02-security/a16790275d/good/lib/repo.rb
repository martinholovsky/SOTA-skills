# frozen_string_literal: true

def since(ts)
  DB[:events].where(Sequel.lit("created_at > ?", ts))
end
