# frozen_string_literal: true

def dump(db, out)
  system("pg_dump", db, "-f", out)
  upload(out)
end
