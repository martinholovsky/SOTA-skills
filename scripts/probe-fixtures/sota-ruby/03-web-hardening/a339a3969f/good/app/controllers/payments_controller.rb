# frozen_string_literal: true

class PaymentsController < ApplicationController
  before_action :authenticate_user!
end
