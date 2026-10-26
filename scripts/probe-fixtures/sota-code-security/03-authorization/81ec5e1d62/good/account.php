<?php
if (!isset($_SESSION['uid'])) {
    header('Location: /login.php'); exit;
}
delete_account($_POST['id']);
