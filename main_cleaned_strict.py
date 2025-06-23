from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from keep_alive import keep_alive  # pastikan file ini ada
import sheet_handler
from datetime import datetime, timedelta
from datetime import datetime
print("Bot started at", datetime.now())

# Aktifkan Flask web server dulu
keep_alive()  # Panggil sebelum bot dijalankan

# Token dan Konstanta
import logging
logging.basicConfig(level=logging.INFO)

import os
TOKEN_BOT = os.getenv("TOKEN_BOT")
print("DEBUG: TOKEN_BOT =", TOKEN_BOT)

QRIS_IMAGE_FILE_ID = "AgACAgUAAxkBAAE2sSdoWN0jOr5K_A5o95kjLpG_TPbalAACJMIxGzsEyVZHtIDsqvhjDwEAAwIAA3kAAzYE"
ADMIN_CHAT_ID = 1147328996
CHANNEL_USERNAME = "@premiumyutub"

user_sync_state = {}
menu_admin = [
    ["📄 Cek Profil", "📦 Lihat Batch"],
    ["🔄 Sinkronkan Data", "📤 Kirim Notifikasi", "📋 Cek Reminder"]
]
menu_user = [
    ["📄 Cek Profil", "📦 Lihat Batch"],
    ["💰 Pembayaran", "🔔 Reminder"],
    ["📬 Contact Admin"]
]
markup_admin = ReplyKeyboardMarkup(menu_admin, resize_keyboard=True)
markup_user = ReplyKeyboardMarkup(menu_user, resize_keyboard=True)

# Middleware join channel info
async def ensure_join_channel(update, context):
    user_id = update.effective_user.id
    if str(user_id) == str(ADMIN_CHAT_ID): return True
    try:
        user_status = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if user_status.status not in ['member', 'administrator', 'creator']:
            keyboard = [[InlineKeyboardButton("🔔 Join Channel Info", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")]]
            markup_inline = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Untuk akses menu, silakan join channel info dulu:",
                reply_markup=markup_inline
            )
            return False
        return True
    except Exception:
        await update.message.reply_text("Bot gagal cek status channel. Coba beberapa saat lagi.")
        return False

# ===== /START HANDLER =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_join_channel(update, context): return
    user_id = update.effective_user.id
    if str(user_id) == str(ADMIN_CHAT_ID):
        total_user = sheet_handler.count_total_user()
        total_batch = len(sheet_handler.get_batch_status())
        welcome = (
            "<b>👑 Selamat Datang di Panel Admin Warsh Store!</b>\n"
            f"👥 <b>Total Pelanggan:</b> <code>{total_user}</code>\n"
            f"🗃️ <b>Total Batch:</b> <code>{total_batch} batch</code>\n\n"
            "Gunakan menu di bawah untuk mengelola semua layanan.\n"
            "Jika ada kendala, ketik ulang /start."
        )
        await update.message.reply_text(welcome, reply_markup=markup_admin, parse_mode="HTML")
    else:
        total_batch = len(sheet_handler.get_batch_status())
        welcome = (
            "<b>👋 Selamat Datang di Bot Patungan YouTube Premium!</b>\n"
            "Bergabunglah bersama komunitas nyaman & aman.\n\n"
            f"<blockquote>🗃️ <b>Total Batch:</b> <code>{total_batch} batch</code></blockquote>\n\n"
            
            "Gunakan menu di bawah untuk cek profil, pembayaran, reminder, atau kontak admin.\n"
            "Jika butuh bantuan, klik Laporan ke Admin.\n\n"
            "✨ <i>Selamat menikmati layanan dari Warsh Store!</i>"
        )
        await update.message.reply_text(welcome, reply_markup=markup_user, parse_mode="HTML")

async def sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_join_channel(update, context): return
    await update.message.reply_text("Masukkan username kamu (tanpa @):")
    user_sync_state[update.effective_chat.id] = "awaiting_username"

# ============= HANDLER MESSAGE ==============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ===== Tambahkan proteksi ini di baris awal! =====
    if update.effective_user is None or update.message is None:
        return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # =========== ADMIN ===========
    if str(user_id) == str(ADMIN_CHAT_ID):
        # Broadcast Notifikasi
        if user_sync_state.get(chat_id) == "broadcast":
            cache = sheet_handler.get_sheet().open_by_key(sheet_handler.SPREADSHEET_ID).worksheet(sheet_handler.CACHE_SHEET_NAME)
            all_rows = cache.get_all_records()
            sukses, gagal = 0, 0
            for row in all_rows:
                try:
                    if row.get("ChatID"):
                        await context.bot.send_message(row["ChatID"], text)
                        sukses += 1
                except: gagal += 1
            await update.message.reply_text(f"✅ Broadcast selesai: {sukses} sukses, {gagal} gagal.")
            user_sync_state.pop(chat_id, None)
            return
        # Kirim Notifikasi
        if text == "📤 Kirim Notifikasi":
            await update.message.reply_text("Ketik pesan yang ingin di-broadcast ke semua pelanggan:")
            user_sync_state[chat_id] = "broadcast"
            return
        # Cek Profil
        if text == "📄 Cek Profil":
            await update.message.reply_text("Masukkan username/email pelanggan:")
            user_sync_state[chat_id] = "cek_profil_admin"
            return
        if user_sync_state.get(chat_id) == "cek_profil_admin":
            profile = sheet_handler.get_profile_by_username(text)
            if not profile:
                await update.message.reply_text("Pelanggan tidak ditemukan.")
            else:
                loyalty = sheet_handler.get_loyalty_tier(profile.get('Tanggal Bergabung', '-'))
                batch = profile.get('Batch Bantu', '-')
                kontak = profile.get('Kontak aktif yang bisa dihubungi', '-')
                reply = (
                    "```\n"
                    f"👤 Username     : {profile.get('Username Bantu', '-')}\n"
                    f"📍 Domisili     : {profile.get('Domisili', '-')}\n"
                    f"📧 Email        : {profile.get('Email yang akan di invite', '-')}\n"
                    f"📅 Bergabung    : {profile.get('Tanggal Bergabung', '-')}\n"
                    f"⏳ Masa Aktif   : {profile.get('Durasi Berlangganan', '-')}\n"
                    f"🆔 ID Telegram  : {profile.get('Kontak aktif yang bisa dihubungi', '-')}\n"
                    f"⭐ Loyalty Tier : {loyalty}\n"
                    f"📦 Batch        : {batch}\n"
                    f"📱 Kontak       : {kontak}\n"
                    "```"
                )
                await update.message.reply_text(reply, parse_mode="Markdown")
            user_sync_state.pop(chat_id, None)
            return
        # Lihat Batch
        if text == "📦 Lihat Batch":
            await pilih_batch(update, context, admin=True, page=0)
            return
        # Sinkron Data
        if text == "🔄 Sinkronkan Data":
            msg = await update.message.reply_text("Menyinkronkan data... Mohon tunggu.")
            try:
                sheet_handler.sync_data()
                await msg.edit_text("✅ Data telah disinkronkan.")
            except Exception as e:
                await msg.edit_text(f"Gagal sinkronisasi data: {e}")
            return
        # Cek Reminder
        if text == "📋 Cek Reminder":
            await reminder_list(update, context, page=0)
            return
        return

    # ========== PELANGGAN ==========
    if user_sync_state.get(chat_id) == "awaiting_username":
        username_input = text
        row = sheet_handler.get_user_by_username(username_input)
        if row:
            sheet_handler.save_chat_id(username_input, chat_id)
            await update.message.reply_text(
                "✅ Username berhasil disinkronkan! Silakan gunakan menu di bawah.",
                reply_markup=markup_user
            )
        else:
            await update.message.reply_text("❌ Username tidak ditemukan di database.")
        user_sync_state.pop(chat_id, None)
        return

    if text == "📄 Cek Profil":
        username = sheet_handler.get_user_by_chat_id(chat_id)
        if not username:
            await update.message.reply_text("❌ Kamu belum sinkronisasi. Ketik /sync dulu.")
            return
        profile = sheet_handler.get_profile_by_username(username)
        if profile:
            loyalty = sheet_handler.get_loyalty_tier(profile.get('Tanggal Bergabung', '-'))
            kontak = profile.get('Kontak aktif yang bisa dihubungi', '-')
            batch = profile.get('Batch Bantu', '-')
            reply = (
                "```\n"
                f"👤 Username     : {profile.get('Username Bantu', '-')}\n"
                f"📍 Domisili     : {profile.get('Domisili', '-')}\n"
                f"📧 Email        : {profile.get('Email yang akan di invite', '-')}\n"
                f"📅 Bergabung    : {profile.get('Tanggal Bergabung', '-')}\n"
                f"⏳ Masa Aktif   : {profile.get('Durasi Berlangganan', '-')}\n"
                f"🆔 ID Telegram  : {chat_id}\n"
                f"⭐ Loyalty Tier : {loyalty}\n"
                f"📦 Batch        : {batch}\n"
                f"📱 Kontak       : {kontak}\n"
                "```"
            )
            await update.message.reply_text(reply, parse_mode="Markdown")
        else:
            await update.message.reply_text("Profil kamu tidak ditemukan.")
        return

    if text == "📦 Lihat Batch":
        await pilih_batch(update, context, admin=False, page=0)
        return

    if text == "💰 Pembayaran":
        keyboard = [[InlineKeyboardButton("✅ Sudah Bayar", callback_data="sudah_bayar")]]
        markup_pay = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            QRIS_IMAGE_FILE_ID,
            caption="Silakan scan QRIS di atas untuk pembayaran. Klik <b>Sudah Bayar</b> setelah transfer.",
            reply_markup=markup_pay,
            parse_mode="HTML"
        )
        return

    if text == "🔔 Reminder":
        status = sheet_handler.get_reminder_status(chat_id)
        if status == "aktif":
            sheet_handler.set_reminder_status(chat_id, "nonaktif")
            await update.message.reply_text("🔕 Reminder dinonaktifkan. Kamu tidak akan menerima pengingat otomatis.")
        else:
            sheet_handler.set_reminder_status(chat_id, "aktif")
            await update.message.reply_text("🔔 Reminder aktif! Kamu akan diingatkan H-7 dan H-3 sebelum masa aktif habis.")
        return
    if text == "📬 Contact Admin":
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/6287870334162")],
            [InlineKeyboardButton("✈️ Telegram", url="https://t.me/warshstore")],
        ]
        markup_admin = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Hubungi admin via tombol berikut:",
            reply_markup=markup_admin
        )
        return

# ================= Handler Callback =================

async def handle_sudah_bayar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
        await query.answer()
chat_id = query.from_user.id
    username = sheet_handler.get_user_by_chat_id(chat_id)
    profile = sheet_handler.get_profile_by_username(username)
    kode_invoice = sheet_handler.generate_invoice_code()
    wib_time = datetime.utcnow() + timedelta(hours=7)
    waktu = wib_time.strftime('%d/%m/%Y %H:%M:%S')
    invoice = sheet_handler.get_invoice(profile, kode_invoice, waktu)
    kontak = profile.get('Kontak aktif yang bisa dihubungi', '-')
    # Notif pelanggan
    await query.edit_message_caption(
        caption="✅ Pembayaran kamu sudah dicatat, sedang dicek admin.\nTunggu konfirmasi.", parse_mode="HTML")
    # Notif admin
    tombol = [
        [InlineKeyboardButton("Konfirmasi Pembayaran", callback_data=f"konfirmasi_bayar_{chat_id}_{kode_invoice}")]
    ]
    await context.bot.send_message(
        ADMIN_CHAT_ID,
        f"💸 Pembayaran baru dari <b>{username}</b> ({kontak})\n\n{invoice}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(tombol)
    )

async def handle_konfirmasi_bayar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    chat_id = int(parts[2])
    kode_invoice = parts[3]
    username = sheet_handler.get_user_by_chat_id(chat_id)
    profile = sheet_handler.get_profile_by_username(username)
    invoice = sheet_handler.get_invoice(profile, kode_invoice)
    # Info ke pelanggan
    await context.bot.send_message(
        chat_id,
        f"✅ <b>Pembayaran kamu telah dikonfirmasi admin!</b>\n\n{invoice}",
        parse_mode="HTML"
    )
    # Info ke channel
    await context.bot.send_message(
        CHANNEL_USERNAME,
        f"<b>🧾 TRANSAKSI BERHASIL</b>\n{invoice}",
        parse_mode="HTML"
    )
    await query.answer("Pembayaran dikonfirmasi & invoice dikirim ke channel info!", show_alert=True)
    await query.edit_message_reply_markup(reply_markup=None)

# ======= Handler Batch & Pagination =======
async def pilih_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, admin=False, page=0):
    batch_data = sheet_handler.get_batch_status()
    per_page = 5
    start, end = page*per_page, (page+1)*per_page
    batchs = batch_data[start:end]
    buttons = []
    for batch in batchs:
        batch_no = batch.get("Batch", "-")
        status = batch.get("Status", "-").lower()
        icon = "🔴" if "full" in status else "🟢"
        tipe = "admin" if admin else "user"
        buttons.append([InlineKeyboardButton(f"{icon} {batch_no} {status.title()}",
                         callback_data=f"lihat_{batch_no}_{tipe}_{page}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Kembali", callback_data=f"batchpage_{tipe}_{page-1}"))
    if end < len(batch_data):
        nav.append(InlineKeyboardButton("➡️ Lanjut", callback_data=f"batchpage_{tipe}_{page+1}"))
    markup = InlineKeyboardMarkup(buttons+[nav] if nav else buttons)
    msg = "Pilih batch untuk lihat detail anggota:"
    if getattr(update, "message", None):
        await update.message.reply_text(msg, reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(msg, reply_markup=markup)

async def show_batch_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
        await query.answer()
_, batch_no, tipe, page = query.data.split("_")
    anggota_data = sheet_handler.get_all_batch_members()
    anggota = anggota_data.get(batch_no, [])
    reply = f"📦 Anggota Batch {batch_no}:\n"
    for idx, p in enumerate(anggota[:5]):
        email = p['Email yang akan di invite']
        reply += f"{idx+1}. {email if tipe=='admin' else sheet_handler.censor_email(email)}\n"
    back_btn = [[InlineKeyboardButton("⬅️ Kembali", callback_data=f"batchpage_{tipe}_{page}")]]
    await query.edit_message_text(reply, reply_markup=InlineKeyboardMarkup(back_btn))

async def batch_page_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
        await query.answer()
_, tipe, page = query.data.split("_")
    await pilih_batch(update, context, admin=(tipe=="admin"), page=int(page))

# ======= Handler Reminder List & Detail (Admin) =======
async def reminder_list(update, context, page=0):
    client = sheet_handler.get_sheet()
    sheet = client.open_by_key(sheet_handler.SPREADSHEET_ID).worksheet(sheet_handler.SHEET_NAME)
    data = sheet.get_all_records()

    def parse_tempo(row):
        t = row.get("Tempo", "")
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(t, fmt)
            except:
                continue
        return datetime.max
    data.sort(key=parse_tempo)

    per_page = 10
    now = datetime.utcnow() + timedelta(hours=7)  # WIB
    users = []
    for row in data:
        username = row.get("Username Bantu", "-")
        tempo = row.get("Tempo", "")
        sisa_hari = "-"
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                tempo_dt = datetime.strptime(tempo, fmt)
                sisa = (tempo_dt - now).days
                sisa_hari = str(sisa)
                break
            except:
                continue
        users.append((username, sisa_hari))

    start, end = page*per_page, (page+1)*per_page
    btns = [
        [InlineKeyboardButton(f"{u[0]} - {u[1]} hari", callback_data=f"reminderdetail_{u[0]}_{page}")]
        for u in users[start:end]
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"reminderpage_{page-1}"))
    if end < len(users):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"reminderpage_{page+1}"))
    if nav:
        btns.append(nav)
    markup = InlineKeyboardMarkup(btns)
    if getattr(update, "message", None):
        await update.message.reply_text(
            "Cek reminder user (urut dari tempo terdekat):", reply_markup=markup
        )
    else:
        await update.callback_query.edit_message_text(
            "Cek reminder user (urut dari tempo terdekat):", reply_markup=markup
        )

async def reminder_page_nav(update, context):
    query = update.callback_query
        await query.answer()
page = int(query.data.replace("reminderpage_", ""))
    await reminder_list(query, context, page)

async def reminder_detail(update, context):
    query = update.callback_query
        await query.answer()
username, page = query.data.replace("reminderdetail_", "").split("_")
    profile = sheet_handler.get_profile_by_username(username)
    if not profile:
        await query.answer("Tidak ditemukan.")
        return
    kontak = profile.get('Kontak aktif yang bisa dihubungi', '-')
    reply = (
        "```\n"
        f"👤 Username     : {profile.get('Username Bantu', '-')}\n"
        f"📍 Domisili     : {profile.get('Domisili', '-')}\n"
        f"📧 Email        : {profile.get('Email yang akan di invite', '-')}\n"
        f"📅 Bergabung    : {profile.get('Tanggal Bergabung', '-')}\n"
        f"⏳ Masa Aktif   : {profile.get('Durasi Berlangganan', '-')}\n"
        f"🆔 ID Telegram  : {profile.get('Kontak aktif yang bisa dihubungi', '-')}\n"
        f"📦 Batch        : {profile.get('Batch Bantu', '-')}\n"
        f"📱 Kontak       : {kontak}\n"
        "```"
    )
    btn = [[InlineKeyboardButton("⬅️ Kembali", callback_data=f"reminderpage_{page}")]]
    await query.edit_message_text(reply, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(btn))

def main():
    app = ApplicationBuilder().token(TOKEN_BOT).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sync", sync))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # CallbackQueryHandler: Semua menu tombol inline & pagination
    app.add_handler(CallbackQueryHandler(handle_sudah_bayar, pattern="^sudah_bayar$"))
    app.add_handler(CallbackQueryHandler(handle_konfirmasi_bayar, pattern="^konfirmasi_bayar_"))
    app.add_handler(CallbackQueryHandler(show_batch_detail, pattern="^lihat_"))
    app.add_handler(CallbackQueryHandler(batch_page_nav, pattern="^batchpage_"))
    app.add_handler(CallbackQueryHandler(reminder_page_nav, pattern="^reminderpage_"))
    app.add_handler(CallbackQueryHandler(reminder_detail, pattern="^reminderdetail_"))
    app.run_polling()

if __name__ == "__main__":
    main()

