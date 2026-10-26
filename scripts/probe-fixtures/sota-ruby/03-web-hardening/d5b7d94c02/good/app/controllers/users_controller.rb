# frozen_string_literal: true

def create
  @user = User.new(user_params)
end
