<?php

declare(strict_types=1);

namespace App\Http;

final class TenantMiddleware
{
    public function handle(Request $request, Kernel $kernel): Response
    {
        TenantContext::$tenant = $request->tenantId();
        return $kernel->handle($request);
    }
}
