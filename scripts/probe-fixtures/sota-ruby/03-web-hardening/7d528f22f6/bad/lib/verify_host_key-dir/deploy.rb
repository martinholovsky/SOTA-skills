# frozen_string_literal: true

def deploy(host)
  Net::SSH.start(host, "deploy", keys: [KEY_PATH]) { |ssh| ssh.exec!("restart") }
end
