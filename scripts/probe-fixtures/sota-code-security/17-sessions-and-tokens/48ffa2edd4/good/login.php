<?php
session_start();
if (login_ok($_POST['user'], $_POST['pass'])) {
    session_regenerate_id(true);
}
