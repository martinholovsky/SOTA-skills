# frozen_string_literal: true

Rails.application.routes.draw do
  post "transfer", to: "transfers#create"
  draw(:admin)
end
