# frozen_string_literal: true

def deploy(host)
  Net::SSH.start(host, "deploy", keys: [KEY_PATH], verify_host_key: :never) { |ssh| ssh.exec!("restart") }
end
