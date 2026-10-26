<?php
declare(strict_types=1);

echo '<p>Results for ', htmlspecialchars($_GET['q'] ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'), '</p>';
