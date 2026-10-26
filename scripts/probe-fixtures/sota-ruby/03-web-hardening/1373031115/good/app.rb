# frozen_string_literal: true

post "/users/:id" do
  User[params[:id]].set_fields(params, %w[name email]).save
end
