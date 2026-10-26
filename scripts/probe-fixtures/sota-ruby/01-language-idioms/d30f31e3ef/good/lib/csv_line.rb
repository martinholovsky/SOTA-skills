# frozen_string_literal: true

def render(rows)
  out = +""
  rows.each { |r| out << r.join(",") << "\n" }
  out
end
