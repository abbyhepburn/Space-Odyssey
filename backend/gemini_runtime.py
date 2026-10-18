"""Small provider circuit breaker; quota failures never trigger retry storms."""
import time

blocked_until = 0.

def cooldown_remaining():
    return max(0., blocked_until-time.monotonic())

def record_failure(exc):
    global blocked_until
    if getattr(exc,'code',None)!=429:return
    delay=60.
    response=getattr(exc,'response',None)
    headers=getattr(response,'headers',{}) or {}
    try:delay=max(delay,float(headers.get('retry-after',0)))
    except (TypeError,ValueError):pass
    details=getattr(exc,'details',None)
    def inspect(value):
        nonlocal delay
        if isinstance(value,dict):
            retry=value.get('retryDelay')
            if isinstance(retry,str):
                try:delay=max(delay,float(retry.rstrip('s')))
                except ValueError:pass
            for child in value.values():inspect(child)
        elif isinstance(value,list):
            for child in value:inspect(child)
    inspect(details)
    blocked_until=time.monotonic()+delay
