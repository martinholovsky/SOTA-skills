# frozen_string_literal: true

def index
  pattern = Regexp.new(Regexp.escape(params[:q].to_s[0, 100]), timeout: 0.1)
  @hits = Doc.all.select { |d| d.title.match?(pattern) }
end
