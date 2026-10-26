# frozen_string_literal: true

post "/users/:id" do
  User[params[:id]].set(params).save
end
