<?php
if (!isset($_SESSION['uid'])) {
    header('Location: /login.php');
}
delete_account($_POST['id']);
