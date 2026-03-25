#!/usr/bin/env python3
"""
Real-time High Pitch + Volume Boost Voice Chat Bot
Your voice becomes louder and higher-pitched in Telegram VC
"""

import asyncio
import numpy as np
import sounddevice as sd
import librosa
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import InputStream, InputAudioStream

# ====================== CONFIG ======================
API_ID = 12345678          # ← Get from my.telegram.org
API_HASH = "your_api_hash_here"
PHONE = "+91xxxxxxxxxx"    # ← Your Telegram phone number

# How much to boost
VOLUME_BOOST = 3.0         # 2.0 = double volume, 4.0 = very loud (be careful)
PITCH_SHIFT = 8            # Semitones: +12 = one octave higher, +7 ~ high pitch

# ===================================================

app = Client("highpitch_vc", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE)
call = PyTgCalls(app)

is_streaming = False
stream_task = None

async def real_time_highpitch_stream(chat_id: int):
    global is_streaming
    is_streaming = True

    print(f"🎤 Starting real-time high pitch + boost in chat {chat_id}")

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)

        # Convert to float32
        audio = indata[:, 0].astype(np.float32)

        # === VOLUME BOOST ===
        audio = np.clip(audio * VOLUME_BOOST, -1.0, 1.0)

        # === PITCH SHIFT (real-time) ===
        # librosa pitch_shift works on small chunks reasonably well
        try:
            shifted = librosa.effects.pitch_shift(
                y=audio,
                sr=48000,
                n_steps=PITCH_SHIFT,
                bins_per_octave=12
            )
            # Keep same length
            if len(shifted) > len(audio):
                shifted = shifted[:len(audio)]
            elif len(shifted) < len(audio):
                shifted = np.pad(shifted, (0, len(audio) - len(shifted)))
        except:
            shifted = audio  # fallback

        # Convert back to int16 for Telegram (required format)
        out = np.clip(shifted * 32767, -32768, 32767).astype(np.int16)

        # Send to PyTgCalls (it expects bytes)
        try:
            call.send_audio(chat_id, out.tobytes())
        except:
            pass  # ignore small errors

    try:
        with sd.InputStream(
            samplerate=48000,
            channels=1,
            dtype='float32',
            blocksize=960,          # ~20ms chunks - good for low latency
            callback=audio_callback
        ):
            while is_streaming:
                await asyncio.sleep(0.1)
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        is_streaming = False
        print("Stream stopped")


@app.on_message(filters.command("join") & filters.group)
async def join_vc(client: Client, message: Message):
    global stream_task
    chat_id = message.chat.id

    try:
        await call.join_group_call(
            chat_id,
            InputStream(
                InputAudioStream(
                    path="input.raw",  # dummy, we use custom streaming
                    bitrate=48000,
                )
            ),
            stream_type=StreamType().local_stream
        )
        await message.reply_text("✅ Joined Voice Chat!\n🎤 High pitch + boost activated.\nSpeak now!")
        
        # Start real-time processing
        if stream_task is None or stream_task.done():
            stream_task = asyncio.create_task(real_time_highpitch_stream(chat_id))
            
    except Exception as e:
        await message.reply_text(f"Error joining: {e}")


@app.on_message(filters.command("leave") & filters.group)
async def leave_vc(client: Client, message: Message):
    global is_streaming, stream_task
    chat_id = message.chat.id
    
    is_streaming = False
    if stream_task:
        stream_task.cancel()
    
    try:
        await call.leave_group_call(chat_id)
        await message.reply_text("👋 Left Voice Chat")
    except:
        await message.reply_text("Already left or error")


@app.on_message(filters.command("boost") & filters.group)
async def change_boost(client: Client, message: Message):
    global VOLUME_BOOST
    try:
        new_boost = float(message.text.split()[1])
        VOLUME_BOOST = max(0.5, min(6.0, new_boost))  # limit between 0.5x and 6x
        await message.reply_text(f"🔊 Volume boost set to **{VOLUME_BOOST}x**")
    except:
        await message.reply_text(f"Current boost: {VOLUME_BOOST}x\nUsage: /boost 3.5")


@app.on_message(filters.command("pitch") & filters.group)
async def change_pitch(client: Client, message: Message):
    global PITCH_SHIFT
    try:
        new_pitch = int(message.text.split()[1])
        PITCH_SHIFT = max(-12, min(24, new_pitch))
        await message.reply_text(f"🎵 Pitch shift set to **{PITCH_SHIFT}** semitones")
    except:
        await message.reply_text(f"Current pitch: +{PITCH_SHIFT} semitones\nUsage: /pitch 10")


async def main():
    await app.start()
    await call.start()
    print("🤖 High Pitch Voice Bot is running...")
    print("Commands in group:")
    print("   /join   → Join VC with high pitch boost")
    print("   /leave  → Leave VC")
    print("   /boost 3.5 → Change volume")
    print("   /pitch 10  → Change pitch (higher = more chipmunk)")
    
    await asyncio.Event().wait()  # keep running


if __name__ == "__main__":
    asyncio.run(main())

i want dockerfile for this
