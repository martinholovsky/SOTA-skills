# frozen_string_literal: true

def update
  if request.get?
    render :edit
  else
    current_user.update!(settings_params)
  end
end
