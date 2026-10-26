# frozen_string_literal: true

def show
  render file: "docs/#{params[:page]}"
end
