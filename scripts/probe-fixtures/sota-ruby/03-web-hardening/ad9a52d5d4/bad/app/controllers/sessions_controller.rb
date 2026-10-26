# frozen_string_literal: true

def create
  redirect_to params[:return_to], allow_other_host: true
end
