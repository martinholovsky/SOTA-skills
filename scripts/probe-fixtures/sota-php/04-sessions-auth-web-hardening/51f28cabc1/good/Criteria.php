<?php
class UserCriteria {
    /**
     * @var string $secure_pass
     */
    public $Password_IsLike;
    public $PwdExpirationDate;
    private $_secretLength = 10;
    public $PwdHistory1;
}
