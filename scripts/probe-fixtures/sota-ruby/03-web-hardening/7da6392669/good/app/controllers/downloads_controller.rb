# frozen_string_literal: true

def show
  report = current_user.reports.find(params[:id])
  send_file report.path, filename: "report.pdf"
end
