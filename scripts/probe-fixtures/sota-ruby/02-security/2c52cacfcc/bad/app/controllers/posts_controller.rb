# frozen_string_literal: true

def index
  @posts = Post.order(params[:sort])
end
