# frozen_string_literal: true

def show
  render html: ERB.new(params[:template]).result(binding)
end
