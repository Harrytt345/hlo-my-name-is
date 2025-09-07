from vars import REPO_URL
import os
import re
import sys
import m3u8
import json
import time
import pytz
import asyncio
import requests
import subprocess
import urllib
import urllib.parse
import yt_dlp
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from modules.logs import logging
from bs4 import BeautifulSoup
from modules import saini as helper
from modules.html_handler import html_handler
from modules.drm_handler import drm_handler
from modules import globals
from modules.authorisation import add_auth_user, list_auth_users, remove_auth_user
from modules.broadcast import broadcast_handler, broadusers_handler
from modules.text_handler import text_to_txt
from modules.youtube_handler import ytm_handler, y2t_handler, getcookies_handler, cookies_handler
from modules.utils import progress_bar
from vars import api_url, api_token, token_cp, adda_token, photologo, photoyt, photocp, photozip
from vars import API_ID, API_HASH, BOT_TOKEN, OWNER, CREDIT, AUTH_USERS, TOTAL_USERS, cookies_file_path
from aiohttp import ClientSession, web
from subprocess import getstatusoutput
from pytube import YouTube
from aiohttp import web
import random
from pyromod import listen
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InputMediaPhoto
from pyrogram.errors import FloodWait, PeerIdInvalid, UserIsBlocked, InputUserDeactivated, Unauthorized, AuthKeyUnregistered
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
import aiofiles
import zipfile
import shutil
import ffmpeg
import glob
import psutil
from pathlib import Path

# Global variable to track bot status
bot_status = {
    "running": False,
    "error": None,
    "session_name": None,
    "start_time": None
}

# Enhanced cleanup function for before each download
def cleanup_before_download():
    """Clean up files before starting each download to prevent disk quota issues"""
    print("🧹 Cleaning up before download...")
    try:
        cleanup_count = 0
        
        # Clean temporary directories
        temp_dirs = ['/tmp', './downloads', './temp', './sessions']
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            # Delete all files (not just old ones)
                            os.unlink(file_path)
                            cleanup_count += 1
                        elif os.path.isdir(file_path) and filename != 'bot_' + str(int(time.time()))[:6]:
                            # Don't delete current session folder
                            shutil.rmtree(file_path)
                            cleanup_count += 1
                    except Exception as e:
                        print(f"Error cleaning {file_path}: {e}")
        
        # Clean downloaded files in current directory
        download_patterns = ['*.mp4', '*.mkv', '*.avi', '*.mp3', '*.pdf', '*.zip', '*.txt', '*.html']
        for pattern in download_patterns:
            for file_path in Path('.').glob(pattern):
                try:
                    # Don't delete logs.txt and important config files
                    if file_path.name not in ['logs.txt', 'requirements.txt', 'main.py']:
                        file_path.unlink()
                        cleanup_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        print(f"✅ Cleanup completed. Removed {cleanup_count} files/folders.")
        
        # Check disk space after cleanup
        try:
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            print(f"💾 Disk space after cleanup: {free_gb:.2f}GB free")
        except:
            pass
            
        return cleanup_count
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return 0

def check_disk_space():
    """Check available disk space"""
    try:
        disk_usage = psutil.disk_usage('/')
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        used_percent = (disk_usage.used / disk_usage.total) * 100
        
        print(f"💾 Disk space: {free_gb:.2f}GB free / {total_gb:.2f}GB total ({used_percent:.1f}% used)")
        
        # If less than 1GB free, trigger aggressive cleanup
        if free_gb < 1.0:
            print("⚠️ Low disk space detected! Running cleanup...")
            cleanup_before_download()
            return False
        return True
    except Exception as e:
        print(f"Disk check error: {e}")
        return True

# Enhanced session cleanup function
def clean_session_files():
    """Remove all existing session files to ensure clean start"""
    print("Starting session cleanup...")
    # Delete all session files in the sessions directory
    session_files = glob.glob("./sessions/*.session*")  # This catches .session, .session-journal, etc.
    deleted_count = 0
    for file in session_files:
        try:
            os.remove(file)
            print(f"Deleted old session file: {file}")
            deleted_count += 1
        except Exception as e:
            print(f"Error deleting session file {file}: {e}")

    # Create sessions directory if it doesn't exist
    if not os.path.exists("./sessions"):
        os.makedirs("./sessions", exist_ok=True)
        print("Created sessions directory")

    print(f"Session cleanup completed. Deleted {deleted_count} files.")
    return deleted_count

# Execute session cleanup
clean_session_files()

# Initialize the bot with a unique session name each time
SESSION_NAME = f"./sessions/bot_{int(time.time())}"
bot_status["session_name"] = SESSION_NAME
print(f"Using session file: {SESSION_NAME}")

bot = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Web server for Render health checks
async def health_check(request):
    return web.Response(text="Bot is running")

async def status_check(request):
    """Debug endpoint to check bot status"""
    status_info = {
        "bot_running": bot_status["running"],
        "error": str(bot_status["error"]) if bot_status["error"] else None,
        "session_name": bot_status["session_name"],
        "start_time": bot_status["start_time"],
        "env_vars": {
            "API_ID": os.environ.get('API_ID', 'Not set'),
            "BOT_TOKEN_SET": bool(os.environ.get('BOT_TOKEN')),
            "OWNER_SET": bool(os.environ.get('OWNER')),
            "CREDIT_SET": bool(os.environ.get('CREDIT')),
            "PORT": os.environ.get('PORT', 'Not set')
        },
        "session_files": glob.glob("./sessions/*.session*"),
        "working_directory": os.getcwd()
    }
    return web.json_response(status_info)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/status', status_check)
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")
    print(f"Status endpoint available at: http://0.0.0.0:{port}/status")
    return runner

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_message(filters.command("start"))
async def start(bot, m: Message):
    user_id = m.chat.id
    if user_id not in TOTAL_USERS:
        TOTAL_USERS.append(user_id)
    user = await bot.get_me()
    mention = user.mention
    caption = f"🌟 Welcome {m.from_user.mention} ! 🌟"
    start_message = await bot.send_photo(
        chat_id=m.chat.id,
        photo="https://envs.sh/GVI.jpg",
        caption=caption
    )
    await asyncio.sleep(1)
    await start_message.edit_text(
        f"🌟 Welcome {m.from_user.first_name}! 🌟\n\n" +
        f"Initializing Uploader bot... 🤖\n\n"
        f"Progress: [⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️] 0%\n\n"
    )
    await asyncio.sleep(1)
    await start_message.edit_text(
        f"🌟 Welcome {m.from_user.first_name}! 🌟\n\n" +
        f"Loading features... ⏳\n\n"
        f"Progress: [🟥🟥🟥⬜️⬜️⬜️⬜️⬜️⬜️⬜️] 25%\n\n"
    )
    await asyncio.sleep(1)
    await start_message.edit_text(
        f"🌟 Welcome {m.from_user.first_name}! 🌟\n\n" +
        f"This may take a moment, sit back and relax! 😊\n\n"
        f"Progress: [🟧🟧🟧🟧🟧⬜️⬜️⬜️⬜️⬜️] 50%\n\n"
    )
    await asyncio.sleep(1)
    await start_message.edit_text(
        f"🌟 Welcome {m.from_user.first_name}! 🌟\n\n" +
        f"Checking subscription status... 🔍\n\n"
        f"Progress: [🟨🟨🟨🟨🟨🟨🟨🟨⬜️⬜️] 75%\n\n"
    )
    await asyncio.sleep(1)
    if m.chat.id in AUTH_USERS:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Commands", callback_data="cmd_command")],
            [InlineKeyboardButton("💎 Features", callback_data="feat_command"), InlineKeyboardButton("⚙️ Settings", callback_data="setttings")],
            [InlineKeyboardButton("💳 Plans", callback_data="upgrade_command")],
            [InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}"), InlineKeyboardButton(text="🛠️ Repo", url=REPO_URL)],
        ])
        await start_message.edit_text(
            f"🌟 Welcome {m.from_user.first_name}! 🌟\n\n" +
            f"Great! You are a premium member!\n"
            f"Use button : **✨ Commands** to get started 🌟\n\n"
            f"If you face any problem contact - [{CREDIT}](tg://openmessage?user_id={OWNER})\n",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )
    else:
        await asyncio.sleep(2)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Commands", callback_data="cmd_command")],
            [InlineKeyboardButton("💎 Features", callback_data="feat_command"), InlineKeyboardButton("⚙️ Settings", callback_data="setttings")],
            [InlineKeyboardButton("💳 Plans", callback_data="upgrade_command")],
            [InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}"), InlineKeyboardButton(text="🛠️ Repo", url=REPO_URL)],
        ])
        await start_message.edit_text(
            f" 🎉 Welcome {m.from_user.first_name} to DRM Bot! 🎉\n\n"
            f"**You are currently using the free version.** 🆓\n\n... I'm here to make your life easier by downloading videos from your **.txt** file 📄 and uploading them directly to Telegram!\n\n**Want to get started? Press /id**\n\n💬 Contact : [{CREDIT}](tg://openmessage?user_id={OWNER}) to Get The Subscription 🎫 and unlock the full potential of your new bot! 🔓\n",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_callback_query(filters.regex("back_to_main_menu"))
async def back_to_main_menu(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id}) in My uploader bot**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Commands", callback_data="cmd_command")],
        [InlineKeyboardButton("💎 Features", callback_data="feat_command"), InlineKeyboardButton("⚙️ Settings", callback_data="setttings")],
        [InlineKeyboardButton("💳 Plans", callback_data="upgrade_command")],
        [InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}"), InlineKeyboardButton(text="🛠️ Repo", url=REPO_URL)],
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://envs.sh/GVI.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )
    await callback_query.answer()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_callback_query(filters.regex("cmd_command"))
async def cmd(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id})\nChoose Button to select Commands**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚻 User", callback_data="user_command"), InlineKeyboardButton("🚹 Owner", callback_data="owner_command")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main_menu")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("user_command"))
async def help_button(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Commands", callback_data="cmd_command")]])
    caption = (
        f"💥 𝐁𝐎𝐓𝐒 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        f"📌 𝗠𝗮𝗶𝗻 𝗙𝗲𝗮𝘁𝘂𝗿𝗲𝘀:\n\n"
        f"➥ /start – Bot Status Check\n"
        f"➥ /y2t – YouTube → .txt Converter\n"
        f"➥ /ytm – YouTube → .mp3 downloader\n"
        f"➥ /t2t – Text → .txt Generator\n"
        f"➥ /t2h – .txt → .html Converter\n"
        f"➥ /stop – Cancel Running Task\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰ \n"
        f"⚙️ 𝗧𝗼𝗼𝗹𝘀 & 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀: \n\n"
        f"➥ /cookies – Update YT Cookies\n"
        f"➥ /id – Get Chat/User ID\n"
        f"➥ /info – User Details\n"
        f"➥ /logs – View Bot Activity\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        f"💡 𝗡𝗼𝘁𝗲:\n\n"
        f"• Send any link for auto-extraction\n"
        f"• Send direct .txt file for auto-extraction\n"
        f"• Supports batch processing\n\n"
        f"╭────────⊰◆⊱────────╮\n"
        f" ➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : {CREDIT} 💻\n"
        f"╰────────⊰◆⊱────────╯\n"
    )
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("owner_command"))
async def help_button(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Commands", callback_data="cmd_command")]])
    caption = (
        f"👤 𝐁𝐨𝐭 𝐎𝐰𝐧𝐞𝐫 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬\n\n"
        f"➥ /addauth xxxx – Add User ID\n"
        f"➥ /rmauth xxxx – Remove User ID\n"
        f"➥ /users – Total User List\n"
        f"➥ /broadcast – For Broadcasting\n"
        f"➥ /broadusers – All Broadcasting Users\n"
        f"➥ /reset – Reset Bot\n"
        f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        f"╭────────⊰◆⊱────────╮\n"
        f" ➠ 𝐌𝐚𝐝𝐞 𝐁𝐲 : {CREDIT} 💻\n"
        f"╰────────⊰◆⊱────────╯\n"
    )
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_callback_query(filters.regex("upgrade_command"))
async def upgrade_button(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main_menu")]])
    caption = (
        f" 🎉 Welcome [{first_name}](tg://user?id={user_id}) to DRM Bot! 🎉\n\n"
        f"You can have access to download all Non-DRM+AES Encrypted URLs 🔐 including\n\n"
        f"... • 📚 Appx Zip+Encrypted Url\n"
        f"• 🎓 Classplus DRM+ NDRM\n"
        f"• 🧑🏫 PhysicsWallah DRM\n"
        f"• 📚 CareerWill + PDF\n"
        f"• 🎓 Khan GS\n"
        f"• 🎓 Study Iq DRM\n"
        f"• 🚀 APPX + APPX Enc PDF\n"
        f"• 🎓 Vimeo Protection\n"
        f"• 🎓 Brightcove Protection\n"
        f"• 🎓 Visionias Protection\n"
        f"• 🎓 Zoom Video\n"
        f"• 🎓 Utkarsh Protection(Video + PDF)\n"
        f"• 🎓 All Non DRM+AES Encrypted URLs\n"
        f"• 🎓 MPD URLs if the key is known (e.g., Mpd_url?key=key XX:XX)\n\n"
        f"**💸 Subscription Price**\n\n"
        f"• 🗓 **Weekly** - ₹ 120/-\n"
        f"• 🗓 **Monthly** - ₹ 350/-\n"
        f"• 🎯 **Demo** - ₹ 25 (1 day)\n\n"
        f"**🏆 Premium Benefits**\n"
        f"• ✅ All DRM Content Support\n"
        f"• 🚀 High-Speed Downloads\n"
        f"• 🔒 Private Bot Access\n"
        f"• 💯 24/7 Support\n"
        f"• 📈 No Download Limits\n\n"
        f"💬 Contact : [{CREDIT}](tg://openmessage?user_id={OWNER}) for Subscription 🎫\n"
    )
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://envs.sh/GVI.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_callback_query(filters.regex("setttings"))
async def settings(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id}) to Bot Settings**\n**Choose the Option you want to Change**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Caption Style", callback_data="caption_command"), InlineKeyboardButton("📄 File Name", callback_data="file_name_command")],
        [InlineKeyboardButton("🌟 Thumbnail", callback_data="thummbnail_command"), InlineKeyboardButton("🏷️ Credit", callback_data="credit_command")],
        [InlineKeyboardButton("🎨 Watermark", callback_data="wattermark_command"), InlineKeyboardButton("🔗 Token", callback_data="set_token_command")],
        [InlineKeyboardButton("🎞️ Video Quality", callback_data="quality_command"), InlineKeyboardButton("🏷️ Topic", callback_data="topic_command")],
        [InlineKeyboardButton("🔄 Reset Settings", callback_data="resset_command")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main_menu")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("credit_command"))
async def handle_caption(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit("**Send Credit Name**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        globals.CR = input_msg.text
        await editable.edit(f"✅ Credit Name `{globals.CR}` set successfully !", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("quality_command"))
async def handle_caption(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit("**Send Quality**\n144 | 240 | 360 | 480 | 720 | 1080", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        globals.raw_text2 = input_msg.text
        if globals.raw_text2 == "144":
            globals.quality = "256x144"
            globals.res = "256x144"
        elif globals.raw_text2 == "240":
            globals.quality = "426x240"
            globals.res = "426x240"
        elif globals.raw_text2 == "360":
            globals.quality = "640x360"
            globals.res = "640x360"
        elif globals.raw_text2 == "480":
            globals.quality = "854x480"
            globals.res = "854x480"
        elif globals.raw_text2 == "720":
            globals.quality = "1280x720"
            globals.res = "1280x720"
        elif globals.raw_text2 == "1080":
            globals.quality = "1920x1080"
            globals.res = "1920x1080"
        else:
            globals.res = "854x480"
            globals.raw_text2 = "480"
        
        await editable.edit(f"✅ Quality **{globals.raw_text2}p** selected !", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("set_token_command"))
async def set_token(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id}) to Token Settings**\n**Choose the Token you want to Set**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📘 Classplus Token", callback_data="cp_token_command")],
        [InlineKeyboardButton("🧑🏫 PhysicsWallah Token", callback_data="pw_token_command")],
        [InlineKeyboardButton("📚 CareerWill Token", callback_data="cw_token_command")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("thummbnail_command"))
async def thumbnail(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id}) to Thumbnail Settings**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Video Thumbnail", callback_data="viideo_thumbnail_command")],
        [InlineKeyboardButton("📄 PDF Thumbnail", callback_data="pddf_thumbnail_command")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("wattermark_command"))
async def watermark(client, callback_query):
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    caption = f"✨ **Welcome [{first_name}](tg://user?id={user_id}) to Watermark Settings**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 Video Watermark", callback_data="video_watermark_command")],
        [InlineKeyboardButton("📄 PDF Watermark", callback_data="pdf_watermark_command")],
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_00000000fc2461fbbdd6bc500cecbff8_conversation_id6874702c-9760-800e-b0bf-8e0bcf8a3833message_id964012ce-7ef5-4ad4-88e0-1c41ed240c03-1-1.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("caption_command"))
async def handle_caption(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit("**Caption Style 1**\n**🎥**[{str(count).zfill(3)}] {name1} [{res}p].{ext}\n\n**Extracted by➤**{CR}\n**Batch Name :**{b_name}\n\n\n**Caption Style 2**\n**📹**Vid Id: {str(count).zfill(3)}\n**Video Title :** `{name1} [{res}p].{ext}`\n\n\n**Extracted by➤**{CR}\nBatch Name :{b_name}\n\n**——— ✦ {str(count).zfill(3)} ✦ ———**\n\n🎞️ **Title** : `{name1}`\n**├── Extention : {extension}.{ext}**\n**├── Resolution : [{res}]**\n📚 **Course : {b_name}**\n\n🌟 **Extracted By : {credit}**\n\n**Caption Style 3**\n\n**{str(count).zfill(3)}.** {name1} [{res}p].{ext}\n\n**Send Your Caption Style eg. /cc1 or /cc2 or /cc3**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/cc1":
            globals.caption = '/cc1'
            await editable.edit(f"✅ Caption Style 1 Updated!", reply_markup=keyboard)
        elif input_msg.text.lower() == "/cc2":
            globals.caption = '/cc2'
            await editable.edit(f"✅ Caption Style 2 Updated!", reply_markup=keyboard)
        else:
            globals.caption = input_msg.text
            await editable.edit(f"✅ Caption Style 3 Updated!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("file_name_command"))
async def handle_caption(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit("**Send End File Name or Send /d**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/d":
            globals.endfilename = '/d'
            await editable.edit(f"✅ End File Name Disabled !", reply_markup=keyboard)
        else:
            globals.endfilename = input_msg.text
            await editable.edit(f"✅ End File Name `{globals.endfilename}` is enabled!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("viideo_thumbnail_command"))
async def video_thumbnail(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="thummbnail_command")]])
    editable = await callback_query.message.edit(f"Send the Video Thumb URL or Send /d \n\n**Note- For document format send : No**\n", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.startswith("http://") or input_msg.text.startswith("https://"):
            globals.thumb = input_msg.text
            await editable.edit(f"✅ Thumbnail set successfully from the URL !", reply_markup=keyboard)
        elif input_msg.text.lower() == "/d":
            globals.thumb = "/d"
            await editable.edit(f"✅ Thumbnail set to default !", reply_markup=keyboard)
        else:
            globals.thumb = input_msg.text
            await editable.edit(f"✅ Video in Document Format is enabled !", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n\n**Note- For document format send : No**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("pddf_thumbnail_command"))
async def pdf_thumbnail_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="thummbnail_command")]])
    caption = ("**📄 PDF Thumbnail Settings**\n\nSend the PDF thumbnail URL or send /d for default\n\n**Current PDF Thumbnail:** Default")
    editable = await callback_query.message.edit(caption, reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.startswith("http://") or input_msg.text.startswith("https://"):
            globals.pdfthumb = input_msg.text
            await editable.edit(f"✅ PDF Thumbnail set successfully!", reply_markup=keyboard)
        elif input_msg.text.lower() == "/d":
            globals.pdfthumb = "/d"
            await editable.edit(f"✅ PDF Thumbnail set to default!", reply_markup=keyboard)
        else:
            globals.pdfthumb = input_msg.text
            await editable.edit(f"✅ PDF Thumbnail set!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("cp_token_command"))
async def handle_token(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="set_token_command")]])
    editable = await callback_query.message.edit("**Send Classplus Token**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        globals.cptoken = input_msg.text
        await editable.edit(f"✅ Classplus Token set successfully !\n\n**Token:** `{globals.cptoken}`", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("pw_token_command"))
async def handle_token(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="set_token_command")]])
    editable = await callback_query.message.edit("**Send Physics Wallah Same Batch Token**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        globals.pwtoken = input_msg.text
        await editable.edit(f"✅ Physics Wallah Token set successfully !\n\n**Token:** `{globals.pwtoken}`", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("cw_token_command"))
async def handle_token(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="set_token_command")]])
    editable = await callback_query.message.edit("**Send Carrerwill Token**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/d":
            globals.cwtoken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUChBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
            await editable.edit(f"✅ Carrerwill Token set successfully as default !", reply_markup=keyboard)
        else:
            globals.cwtoken = input_msg.text
            await editable.edit(f"✅ Carrerwill Token set successfully !\n\n**Token:** `{globals.cwtoken}`", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("video_watermark_command"))
async def video_watermark(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="wattermark_command")]])
    editable = await callback_query.message.edit(f"**Send Video Watermark text or Send /d**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/d":
            globals.vidwatermark = "/d"
            await editable.edit(f"**Video Watermark Disabled ✅** !", reply_markup=keyboard)
        else:
            globals.vidwatermark = input_msg.text
            await editable.edit(f"Video Watermark `{globals.vidwatermark}` enabled ✅!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("pdf_watermark_command"))
async def pdf_watermark_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="wattermark_command")]])
    caption = ("**📄 PDF Watermark Settings**\n\nSend watermark text for PDFs or send /d to disable\n\n**Current PDF Watermark:** Disabled")
    editable = await callback_query.message.edit(caption, reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/d":
            globals.pdfwatermark = "/d"
            await editable.edit(f"**PDF Watermark Disabled ✅**", reply_markup=keyboard)
        else:
            globals.pdfwatermark = input_msg.text
            await editable.edit(f"PDF Watermark `{globals.pdfwatermark}` enabled ✅!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("topic_command"))
async def video_watermark(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit(f"**If you want to enable topic in caption: send /yes or send /d**\n\n**Note: Topic fetch from (bracket) in title.**", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/yes":
            globals.topic = "/yes"
            await editable.edit(f"**Topic enabled in Caption ✅** !", reply_markup=keyboard)
        else:
            globals.topic = input_msg.text
            await editable.edit(f"Topic disabled in Caption ✅!", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n**Note: Topic fetch from (bracket) in title.**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("resset_command"))
async def credit(client, callback_query):
    user_id = callback_query.from_user.id
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data="setttings")]])
    editable = await callback_query.message.edit(f"If you want to reset settings send /yes or Send /no", reply_markup=keyboard)
    input_msg = await bot.listen(editable.chat.id)
    try:
        if input_msg.text.lower() == "/yes":
            globals.caption = '/cc1'
            globals.endfilename = '/d'
            globals.thumb = '/d'
            globals.CR = f"{CREDIT}"
            globals.cwtoken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUChBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg'
            globals.cptoken = "cptoken"
            globals.pwtoken = "pwtoken"
            globals.vidwatermark = '/d'
            globals.raw_text2 = '480'
            globals.quality = '480p'
            globals.res = '854x480'
            globals.topic = '/d'
            await editable.edit(f"✅ Settings reset as default !", reply_markup=keyboard)
        else:
            await editable.edit(f"✅ Settings Not Changed !", reply_markup=keyboard)
    except Exception as e:
        await editable.edit(f"**Error:**\n`{str(e)}`", reply_markup=keyboard)
    finally:
        await input_msg.delete()

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_callback_query(filters.regex("feat_command"))
async def feature_button(client, callback_query):
    caption = "**✨ My Premium BOT Features :**"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Auto Pin Batch Name", callback_data="pin_command")],
        [InlineKeyboardButton("💧 Watermark", callback_data="watermark_command"), InlineKeyboardButton("🔄 Reset", callback_data="reset_command")],
        [InlineKeyboardButton("🖨️ Bot Working Logs", callback_data="logs_command")],
        [InlineKeyboardButton("🖋️ File Name", callback_data="custom_command"), InlineKeyboardButton("🏷️ Title", callback_data="titlle_command")],
        [InlineKeyboardButton("🎥 YouTube", callback_data="yt_command")],
        [InlineKeyboardButton("🌐 HTML", callback_data="html_command")],
        [InlineKeyboardButton("📝 Text File", callback_data="txt_maker_command"), InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_command")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main_menu")]
    ])
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("pin_command"))
async def pin_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**Auto Pin 📌 Batch Name :**\n\nAutomatically Pins the Batch Name in Channel or Group, If Starting from the First Link."
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("watermark_command"))
async def watermark_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**Custom Watermark :**\n\nSet Your Own Custom Watermark on Videos for Added Personalization."
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("reset_command"))
async def restart_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**🔄 Reset Command:**\n\nIf You Want to Reset or Restart Your Bot, Simply Use Command /reset."
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("logs_command"))
async def pin_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**🖨️ Bot Working Logs:**\n\n◆/logs - Bot Send Working Logs in .txt File."
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("custom_command"))
async def custom_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**🖋️ Custom File Name:**\n\nSupport for Custom Name before the File Extension.\nAdd name ..when txt is uploading"
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("titlle_command"))
async def titlle_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**Custom Title Feature :**\nAdd and customize titles at the starting\n**NOTE 📍 :** The Titile must enclosed within (Title), Best For appx's .txt file."
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("broadcast_command"))
async def pin_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**📢 Broadcasting Support:**\n\n◆/broadcast - 📢 Broadcast to All Users.\n◆/broadusers - 👁️ To See All Broadcasting User"
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("txt_maker_command"))
async def editor_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**🤖 Available Commands 🗓️**\n◆/t2t for text to .txt file\n"
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://tinypic.host/images/2025/07/14/file_000000002d44622f856a002a219cf27aconversation_id68747543-56d8-800e-ae47-bb6438a09851message_id8e8cbfb5-ea6c-4f59-974a-43bdf87130c0.png",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,...... ..,
@bot.on_callback_query(filters.regex("yt_command"))
async def y2t_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**YouTube Commands:**\n\n◆/y2t - 🔪 YouTube Playlist → .txt Converter\n◆/ytm - 🎶 YouTube → .mp3 downloader\n\n**Note:**"
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://envs.sh/GVi.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_callback_query(filters.regex("html_command"))
async def y2t_button(client, callback_query):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Feature", callback_data="feat_command")]])
    caption = f"**HTML Commands:**\n\n◆/t2h - 🌐 .txt → .html Converter"
    await callback_query.message.edit_media(
        InputMediaPhoto(
            media="https://envs.sh/GVI.jpg",
            caption=caption
        ),
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,

@bot.on_message(filters.command(["id"]))
async def id_command(client, message: Message):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text="Send to Owner", url=f"tg://openmessage?user_id={OWNER}")]])
    chat_id = message.chat.id
    text = f"**◆YouTube → .mp3 downloader\n01. Send YouTube Playlist.txt file\n02. Send single or multiple YouTube links set\nneg.\n`https://www.youtube.com/watch?v=xxxxxx\nhttps://www.youtube.com/watch?v=yyyyyy`\n\nThe ID of this chat id is:**\n`{chat_id}`"
    if str(chat_id).startswith("-100"):
        await message.reply_text(text)
    else:
        await message.reply_text(text, reply_markup=keyboard)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.private & filters.command(["info"]))
async def info(bot: Client, update: Message):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(text="📞 Contact", url=f"tg://openmessage?user_id={OWNER}")]])
    text = (
        f"╭────────────────╮\n"
        f"│✨ **Your Telegram Info**✨ \n"
        f"├────────────────\n"
        f"├🔹**Name :** `{update.from_user.first_name} {update.from_user.last_name if update.from_user.last_name else 'None'}`\n"
        f"├🔹**User ID :** @{update.from_user.username}\n"
        f"├🔹**TG ID :** `{update.from_user.id}`\n"
        f"├🔹**Profile :** {update.from_user.mention}\n"
        f"╰────────────────╯"
    )
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["logs"]))
async def send_logs(client: Client, m: Message):
    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(f"**Error sending logs:**\n**{e}")

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command(["reset"]))
async def restart_handler(_, m):
    if m.chat.id != OWNER:
        return
    else:
        await m.reply_text("𝐁𝐨𝐭 𝐢𝐬 𝐑𝐞𝐬𝐞𝐭𝐢𝐧𝐠...", True)
        os.execl(sys.executable, sys.executable, *sys.argv)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("stop") & filters.private)
async def cancel_handler(client: Client, m: Message):
    if m.chat.id not in AUTH_USERS:
        print(f"User ID not in AUTH_USERS", m.chat.id)
        await bot.send_message(
            m.chat.id,
            f"**__Oopss! You are not a Premium member**__\n"
            f"__**PLEASE /upgrade YOUR PLAN**__\n"
            f"__**Send me your user id for authorization**__\n"
            f"__**Your User id** __- `{m.chat.id}`\n\n"
        )
    else:
        if globals.processing_request:
            globals.cancel_requested = True
            await m.delete()
            cancel_message = await m.reply_text("**🚦 Process cancel request received. Stopping after current process...**")
            await asyncio.sleep(30)
            await cancel_message.delete()
        else:
            await m.reply_text("**⚡ No active process to cancel.**")

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("addauth") & filters.private)
async def call_add_auth_user(client: Client, message: Message):
    await add_auth_user(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("users") & filters.private)
async def call_list_auth_users(client: Client, message: Message):
    await list_auth_users(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("rmauth") & filters.private)
async def call_remove_auth_user(client: Client, message: Message):
    await remove_auth_user(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("broadcast") & filters.private)
async def call_broadcast_handler(client: Client, message: Message):
    await broadcast_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("broadusers") & filters.private)
async def call_broadusers_handler(client: Client, message: Message):
    await broadusers_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("cookies") & filters.private)
async def call_cookies_handler(client: Client, message: Message):
    await cookies_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("y2t") & filters.private)
async def call_y2t_handler(client: Client, message: Message):
    # CLEANUP BEFORE EACH DOWNLOAD PROCESS
    cleanup_before_download()
    check_disk_space()
    await y2t_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("ytm") & filters.private)
async def call_ytm_handler(client: Client, message: Message):
    # CLEANUP BEFORE EACH DOWNLOAD PROCESS
    cleanup_before_download()
    check_disk_space()
    await ytm_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("t2t") & filters.private)
async def call_text_to_txt(client: Client, message: Message):
    cleanup_before_download()  # Cleanup before processing
    await text_to_txt(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
@bot.on_message(filters.command("t2h") & filters.private)
async def call_html_handler(client: Client, message: Message):
    cleanup_before_download()  # Cleanup before processing
    await html_handler(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# Handle file uploads (txt files for extraction)
@bot.on_message(filters.document & filters.private)
async def handle_document(client: Client, message: Message):
    if message.document.mime_type == "text/plain":
        # CLEANUP BEFORE PROCESSING FILE
        cleanup_before_download()
        check_disk_space()
        await helper.main(client, message)

# .....,.....,.......,...,.......,....., .....,.....,.......,...,.......,.....,
# Handle text messages (URLs for extraction)
@bot.on_message(filters.text & filters.private)
async def handle_text(client: Client, message: Message):
    # Skip if it's a command
    if message.text.startswith('/'):
        return
    
    # CLEANUP BEFORE PROCESSING TEXT/URLS
    cleanup_before_download()
    check_disk_space()
    
    # Check if it's a URL or contains links
    if any(url in message.text.lower() for url in ['http', 'www.', '.com', '.org', '.net']):
        await helper.main(client, message)

# Main execution with FIXED event loop
async def main():
    print("=== BOT STARTUP ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"API_ID: {API_ID}")
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}..." if BOT_TOKEN else "NOT SET")
    print(f"OWNER: {OWNER}")
    
    # Initial cleanup
    cleanup_before_download()
    check_disk_space()
    
    # Start web server
    print("Starting web server...")
    web_runner = await start_web_server()
    
    try:
        # Start the bot
        print("Starting Telegram bot...")
        await bot.start()
        
        # Verify bot connection
        me = await bot.get_me()
        print(f"✅ Bot started successfully!")
        print(f"Bot info: @{me.username} - {me.first_name}")
        print(f"Bot ID: {me.id}")
        
        bot_status["running"] = True
        bot_status["start_time"] = time.time()
        bot_status["error"] = None
        
        print("🚀 Bot is now listening for messages...")
        print("Available at: https://hlo-my-name-is.onrender.com")
        print("Status endpoint: https://hlo-my-name-is.onrender.com/status")
        
        # Use pyrogram's idle() to keep bot running and listening
        await idle()
        
    except FloodWait as e:
        print(f"FloodWait error: Waiting {e.value} seconds...")
        bot_status["error"] = f"FloodWait: {e.value}s"
        await asyncio.sleep(e.value)
        
    except (Unauthorized, AuthKeyUnregistered) as e:
        print(f"Authentication error: {e}")
        bot_status["error"] = f"Authentication: {str(e)}"
        
    except Exception as e:
        print(f"Error running bot: {e}")
        bot_status["error"] = f"Runtime: {str(e)}"
        import traceback
        traceback.print_exc()
        
    finally:
        print("Shutting down...")
        await web_runner.cleanup()
        try:
            await bot.stop()
        except:
            pass
        print("Bot stopped.")

if __name__ == "__main__":
    print("🚀 Starting bot...")
    asyncio.run(main())
