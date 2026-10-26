# frozen_string_literal: true

Rails.application.routes.draw do
  match "transfer", to: "transfers#create", via: :all
  draw(:admin)
end
