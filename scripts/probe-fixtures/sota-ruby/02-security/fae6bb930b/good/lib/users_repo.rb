# frozen_string_literal: true

def find(conn, id)
  conn.exec_params("SELECT * FROM users WHERE id = $1", [id])
end
