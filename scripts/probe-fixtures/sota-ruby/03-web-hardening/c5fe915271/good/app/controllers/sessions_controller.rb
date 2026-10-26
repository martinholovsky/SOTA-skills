# frozen_string_literal: true

def create
  redirect_to url_from(params[:return_to]) || root_path
end
