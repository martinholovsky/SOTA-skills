# frozen_string_literal: true

namespace :admin do
  resources :users, only: %i[index show]
end
