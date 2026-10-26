# frozen_string_literal: true

SORTABLE = { "new" => { created_at: :desc }, "old" => { created_at: :asc } }.freeze

def index
  @posts = Post.order(SORTABLE.fetch(params[:sort], SORTABLE["new"]))
end
