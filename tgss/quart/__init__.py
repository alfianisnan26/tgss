import asyncio
from quart import Quart, jsonify, Response, request, send_from_directory
from telethon import TelegramClient
from tgss.internal.config import Config

from tgss.internal.tg import TG
from tgss.internal.db import DB
from tgss.internal.service import Service
from tgss.quart import error
from tgss.internal.model import Video, Filter, WorkerSession
from tgss.internal.cache import AsyncCache
from quart_cors import cors
import os

app = Quart(__name__)
app = cors(app, allow_origin="*")  # Allow requests from any origin

app.register_error_handler(400, error.invalid_request)
app.register_error_handler(404, error.not_found)
app.register_error_handler(405, error.invalid_method)
app.register_error_handler(error.HTTPError, error.http_error)

app.config['RESPONSE_TIMEOUT'] = None
app.config['REQUEST_TIMEOUT'] = 120


db = DB(Config.SQLITE_URL())

svc = None

async def init_service():
    global svc

    client = TelegramClient(Config.SESSION() + "_server", Config.API_ID(), Config.API_HASH())
    await client.start()
    
    cache = AsyncCache(Config.CACHE_TTL())
    asyncio.create_task(cache.start_cleanup_task())
    
    tg = TG(client=client, cache=cache)
    svc = Service(db, tg,
                  ss_export_dir=Config.SS_EXPORT_DIR(),
                  debug=Config.DEBUG(),
                  cache=cache,
                  default_chunk_size=Config.CHUNK_SIZE(),
                  )

@app.before_serving
async def startup():
    await init_service()

@app.route('/')
async def me():
    o = await svc.get_my_info()
    return jsonify({
        'id': o.id,
        'first_name': o.first_name,
        'last_name': o.last_name,
        "username": o.username,
        "phone": o.phone,
    })

@app.route('/dialogs/last_message')
async def last_message_with_dialog():
    dialog_id = request.args.get('dialog_id')
    
    if not dialog_id:
        dialog_id = Config.DIALOG_ID()
    
    last_message = await svc.get_last_video_message(dialog_id)
    if not last_message:
        error.abort(404)
    return jsonify(last_message)

@app.route('/dialogs')
async def dialogs():
    dialogs = await svc.get_available_dialogs()
    return jsonify([{
            'id': o.id,
            'name': o.name,
            'last_message_path': f'/dialogs/last_message?dialog_id={o.id}'
        } for o in dialogs 
    ])

@app.route('/stream')
async def transmit_file():
    chunk_size = request.args.get('chunk_size')
    file_generator, headers, response_code = await svc.transmit_file(
        int(request.args.get('dialog_id')),
        int(request.args.get('message_id')),
        int(chunk_size) if chunk_size else None,
        request.headers.get('Range', 0),
        )
    if response_code == 404:
        error.abort(response_code, 'Message Not Found.')
    if response_code == 400:
        error.abort(response_code, 'Invalid media type.')
    if response_code == 416:
        error.abort(response_code, 'Invalid range.')
        
    return Response(file_generator(), headers=headers, status=response_code)

@app.route('/videos/<int:video_id>/previews')
async def get_video_preview_list(video_id:int):
    previews = svc.get_previews(video_id)
    previews.sort()
    return jsonify(previews)

@app.route('/videos/<int:video_id>/previews/<path:filename>')
async def get_video_preview_ss(video_id:int, filename:str):
    try:
        # Serve the file from the constructed directory path
        return await send_from_directory(os.path.join(Config.SS_EXPORT_DIR(), str(video_id)), filename)
    except FileNotFoundError:
        # If the file is not found, return a 404 error
        error.abort(404)
        
@app.route('/videos')
async def get_video_list():
    limit = request.args.get('limit')
    offset = request.args.get('offset')
    sort_by = request.args.get('sort_by')
    sort_direction = request.args.get('sort_direction')
    id = request.args.get('id')
    message_id = request.args.get('message_id')
    dialog_id = request.args.get('dialog_id')
    status = request.args.get('status')
    
    videos = svc.get_video_list(
        ref=Video(
                id=id,
                message_id=message_id,
                dialog_id=dialog_id,
                status=status,
            ),
        filter=Filter(
                sort_by=sort_by,
                limit=limit,
                offset=offset,
                sort_direction=sort_direction,
            ),
    )
    
    return jsonify([o.to_dict() for o in videos])

@app.route('/sessions')
async def get_session_list():
    limit = request.args.get('limit')
    offset = request.args.get('offset')
    sort_by = request.args.get('sort_by')
    sort_direction = request.args.get('sort_direction')
    id = request.args.get('id')
    user_id = request.args.get('message_id')
    dialog_id = request.args.get('dialog_id')
    
    sessions = svc.get_session_list(
        ref=WorkerSession(
                id=id,
                user_id=user_id,
                dialog_id=dialog_id,
            ),
        filter=Filter(
                sort_by=sort_by,
                limit=limit,
                offset=offset,
                sort_direction=sort_direction,
            ),
    )
    
    return jsonify([o.to_dict() for o in sessions])

@app.route('/videos/<int:video_id>/favorite')
async def switch_video_favorit(video_id:int):
    state, res = svc.switch_video_favorite(video_id)
    if res:
        error.abort(res)
        
    return jsonify({
        'state': state
    })
