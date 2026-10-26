# frozen_string_literal: true

def user_params
  params.require(:user).permit(:name, :email)
end
