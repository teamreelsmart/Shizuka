"""Tiny HTTP endpoint required by managed platforms' TCP/HTTP health checks."""
import os
from aiohttp import web

async def start_health_server():
    app = web.Application()
    app.router.add_get('/', health)
    app.router.add_get('/healthz', health)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', '8080')))
    await site.start()
    return runner

async def health(_request):
    return web.json_response({'status': 'ok'})
