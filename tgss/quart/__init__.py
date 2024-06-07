import asyncio
from quart import Quart, render_template, Response, request
from telethon import TelegramClient
from tgss.internal.config import Config
from tgss.internal.error import abort
from tgss.internal.ffmpeg import FFMPEG
from tgss.internal.tg import TG
from tgss.internal.service import Service
from tgss.internal import error


app = Quart(__name__)

app.register_error_handler(400, error.invalid_request)
app.register_error_handler(404, error.not_found)
app.register_error_handler(405, error.invalid_method)
app.register_error_handler(error.HTTPError, error.http_error)
app.config['RESPONSE_TIMEOUT'] = None

ffmpeg = FFMPEG()

svc = None

async def init_service():
    global svc

    client = TelegramClient(Config.SESSION() + "_server", Config.API_ID(), Config.API_HASH())
    await client.start()

    tg = TG(client=client)
    svc = Service(tg, ffmpeg, Config.STREAM_ENDPOINT())

@app.before_serving
async def startup():
    await init_service()

@app.route('/')
async def me():
    user_info = await svc.get_my_info()
    return await render_template('user_info.html', user_info=user_info)

@app.route('/dialogs')
async def dialogs():
    dialogs = await svc.get_available_dialogs()
    return await render_template('dialogs.html', dialogs=dialogs)

@app.route('/last_message')
async def last_message():
    last_message = await svc.get_last_video_message(Config.DIALOG_ID())
    return await render_template('last_message.html', last_message=last_message)

@app.route('/dialogs/<int:dialog_id>/last_message')
async def last_message_with_dialog(dialog_id = Config.DIALOG_ID):
    last_message = await svc.get_last_video_message(dialog_id)
    return await render_template('last_message.html', last_message=last_message)

@app.route('/stream/<int:message_id>')
async def transmit_file(message_id):
    range_header = request.headers.get('Range', 0)

    file_generator, headers, response_code = await svc.transmit_file(dialog_id=Config.DIALOG_ID(), message_id=message_id, range_header=range_header)
    if response_code == 404:
        abort(response_code, 'Message Not Found.')
    if response_code == 400:
        abort(response_code, 'Invalid media type.')
    if response_code == 416:
        abort(response_code, 'Invalid range.')
        
    return Response(file_generator(), headers=headers, status=response_code)