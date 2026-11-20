# frozen_string_literal: true

def limit_from(params)
  raise ArgumentError, "limit must be finite" unless (limit = Float(params[:limit])).finite?

  [limit, 100.0].min
end
