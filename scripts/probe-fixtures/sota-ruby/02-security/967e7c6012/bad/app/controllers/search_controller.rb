# frozen_string_literal: true

def index
  pattern = Regexp.new(params[:q])
  @hits = Doc.all.select { |d| d.title.match?(pattern) }
end
