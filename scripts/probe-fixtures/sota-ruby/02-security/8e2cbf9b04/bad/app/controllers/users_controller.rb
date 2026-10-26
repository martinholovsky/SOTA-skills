# frozen_string_literal: true

def lookup
  @user = User.where("email = '#{params[:email]}'").first
end
