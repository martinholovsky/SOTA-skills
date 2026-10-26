# frozen_string_literal: true

def limit_from(params)
  limit = Float(params[:limit])
  [limit, 100.0].min
end
