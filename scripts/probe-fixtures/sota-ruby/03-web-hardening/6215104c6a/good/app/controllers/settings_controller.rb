# frozen_string_literal: true

def update
  if request.post?
    current_user.update!(settings_params)
  else
    render :edit
  end
end
