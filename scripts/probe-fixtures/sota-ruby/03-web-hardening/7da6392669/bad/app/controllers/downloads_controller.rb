# frozen_string_literal: true

def show
  send_file params[:path]
end
