import os
import asyncio
import numpy as np
import sounddevice as sd
import librosa
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import InputStream, InputAudioStream

# ====================== CONFIG (via ENV) ======================
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")

# Initial Defaults
VOLUME_BOOST = 3.0         
PITCH_SHIFT = 8            
# =============================================================

if not STRING_SESSION:
    print("❌ Error: STRING_SESSION is not set!")
    exit(1)

app = Client(
    "highpitch_vc", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING_SESSION
)
call = PyTgCalls(app)

is_streaming = False
stream_task = None

async def real_time_highpitch_stream(chat_id: int):
    global is_streaming
    is_streaming = True
    print(f"🎤 Starting real-time stream in chat {chat_id}")

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)
        audio = indata[:, 0].astype(np.float32)
        audio = np.clip(audio * VOLUME_BOOST, -1.0, 1.0)
        try:
            shifted = librosa.effects.pitch_shift(
                y=audio, sr=48000, n_steps=PITCH_SHIFT, bins_per_octave=12
            )
            if len(shifted) > len(audio):
                shifted = shifted[:len(audio)]
            elif len(shifted) < len(audio):
                shifted = np.pad(shifted, (0, len(audio) - len(shifted)))
        except:
            shifted = audio  
        
        out = np.clip(shifted * 32767, -32768, 32767).astype(np.int16)
        try:
            call.send_audio(chat_id, out.tobytes())
        except:
            pass

    try:
        with sd.InputStream(
            samplerate=48000, channels=1, dtype='float32',
            blocksize=960, callback=audio_callback
        ):
            while is_streaming:
                await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        is_streaming = False

@app.on_message(filters.command("join") & filters.group)
async def join_vc(client: Client, message: Message):
    global stream_task
    chat_id = message.chat.id
    try:
        await call.join_group_call(
            chat_id,
            InputStream(InputAudioStream(path="input.raw", bitrate=48000)),
            stream_type=StreamType().local_stream
        )
        await message.reply_text("✅ Joined! High pitch + boost active.")
        if stream_task is None or stream_task.done():
            stream_task = asyncio.create_task(real_time_highpitch_stream(chat_id))
    except Exception as e:
        await message.reply_text(f"Error: {e}")

@app.on_message(filters.command("leave") & filters.group)
async def leave_vc(client: Client, message: Message):
    global is_streaming, stream_task
    is_streaming = False
    if stream_task:
        stream_task.cancel()
    try:
        await call.leave_group_call(message.chat.id)
        await message.reply_text("👋 Left Voice Chat")
    except:
        pass

@app.on_message(filters.command("boost") & filters.group)
async def change_boost(client: Client, message: Message):
    global VOLUME_BOOST
    try:
        VOLUME_BOOST = float(message.text.split()[1])
        await message.reply_text(f"🔊 Boost set to **{VOLUME_BOOST}x**")
    except:
        await message.reply_text("Usage: /boost 3.5")

@app.on_message(filters.command("pitch") & filters.group)
async def change_pitch(client: Client, message: Message):
    global PITCH_SHIFT
    try:
        PITCH_SHIFT = int(message.text.split()[1])
        await message.reply_text(f"🎵 Pitch set to **{PITCH_SHIFT}**")
    except:
        await message.reply_text("Usage: /pitch 10")

async def main():
    await app.start()
    await call.start()
    print("🤖 Bot is running...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
