# frozen_string_literal: true

def create
  @user = User.new(params[:user])
end
