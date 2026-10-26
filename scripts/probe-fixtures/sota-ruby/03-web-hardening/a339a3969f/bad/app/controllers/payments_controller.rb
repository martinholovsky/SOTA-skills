# frozen_string_literal: true

class PaymentsController < ApplicationController
  skip_before_action :verify_authenticity_token
end
