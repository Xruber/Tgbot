import logging
from datetime import datetime, timedelta
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import mysql.connector

# --- 1. CONFIGURATION ---

# !!! IMPORTANT: Replace with your actual credentials and IDs !!!
BOT_TOKEN = "8482042827:AAGUtsTJuJslBETa4o11OHiplainokd5BR8"
ADMIN_ID = @grishasoko  # Replace with the User ID of the single admin (e.g., 123456789)

# MySQL Connection Details
DB_CONFIG = {
    "host": "sql12.freesqldatabase.com",
    "user": "sql12805009",
    "password": "mkXXCLqIil",
    "database": "sql12805009",
}

# Conversation States
(PREDICTION_CHOICE, AWAITING_UTR) = range(2)

# Prediction Options
PREDICTION_PLANS = {
    "1_hour": {"label": "1 Hour - 70₹", "price": 70.00, "duration": 1},
    "1_day": {"label": "1 Day - 300₹", "price": 300.00, "duration": 24},
    "7_day": {"label": "7 Days - 1000₹", "price": 1000.00, "duration": 168},
}

# Placeholder Payment Details
PAYMENT_QR_URL = "https://placehold.co/400x400/0000FF/FFFFFF?text=Payment+QR+Code" # Replace with a real payment image URL
PAYMENT_ID = "YOUR_UPI_ID_HERE"
REGISTER_LINK = "https://example.com/register" # Replace with your actual registration link

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 2. DATABASE HELPER FUNCTIONS ---

def get_db_connection():
    """Establishes and returns a MySQL database connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        logger.error(f"Database Connection Error: {err}")
        return None

def get_admin_id_from_db():
    """Fetches the ADMIN_ID from the database settings table."""
    conn = get_db_connection()
    if not conn:
        return ADMIN_ID # Fallback to hardcoded ID
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key = 'ADMIN_ID'")
        result = cursor.fetchone()
        if result:
            return int(result['setting_value'])
    except Exception as e:
        logger.error(f"Error fetching admin ID: {e}")
    finally:
        cursor.close()
        conn.close()
    return ADMIN_ID # Fallback

# --- 3. KEYBOARD GENERATORS ---

def get_main_keyboard():
    """Generates the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🔗 Register Link", callback_data="link_register"),
            InlineKeyboardButton("🔮 Prediction", callback_data="prediction_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_prediction_options_keyboard():
    """Generates the prediction options inline keyboard."""
    keyboard = []
    for key, plan in PREDICTION_PLANS.items():
        keyboard.append([InlineKeyboardButton(plan["label"], callback_data=f"buy_{key}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_sended_keyboard():
    """Generates the 'sended🟢' button keyboard."""
    keyboard = [
        [InlineKeyboardButton("✅ Sended 🟢", callback_data="payment_sended")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_request_keyboard(request_id):
    """Generates the admin action keyboard for a specific request."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept & Set Time", callback_data=f"admin_accept_{request_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{request_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 4. COMMAND HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends the welcome message and main menu."""
    if update.message:
        user = update.effective_user
        await update.message.reply_text(
            f"Hello {user.first_name}! Welcome to the Prediction Bot. Choose an option below:",
            reply_markup=get_main_keyboard(),
        )
    return ConversationHandler.END

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel to view pending requests."""
    user_id = update.effective_user.id
    admin_id = get_admin_id_from_db()

    if user_id != admin_id:
        await update.message.reply_text("🚫 Access Denied. Only the administrator can use this command.")
        return

    conn = get_db_connection()
    if not conn:
        await update.message.reply_text("Database error. Cannot fetch requests.")
        return

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch requests that have a UTR but are not yet accepted
        cursor.execute(
            "SELECT id, user_id, username, prediction_type, price, utr_number, requested_at "
            "FROM payment_requests "
            "WHERE status = 'PENDING_ADMIN' "
            "ORDER BY requested_at ASC"
        )
        requests = cursor.fetchall()

        if not requests:
            await update.message.reply_text("✅ No pending requests to review.")
            return

        for req in requests:
            message_text = (
                f"🚨 **New Pending Request (ID: {req['id']})**\n"
                f"👤 User: @{req['username']} (ID: {req['user_id']})\n"
                f"📦 Plan: {req['prediction_type']} ({req['price']}₹)\n"
                f"💳 UTR: `{req['utr_number']}`\n"
                f"⏰ Requested: {req['requested_at'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await update.message.reply_text(
                message_text,
                reply_markup=get_admin_request_keyboard(req['id']),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await update.message.reply_text("An internal error occurred while fetching requests.")
    finally:
        cursor.close()
        conn.close()

# --- 5. CALLBACK QUERY HANDLERS (Inline Buttons) ---

async def handle_main_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the main menu button clicks (Register and Prediction)."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "link_register":
        await query.edit_message_text(
            f"Here is your registration link: {REGISTER_LINK}",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    elif data == "prediction_menu":
        user_id = query.from_user.id
        
        # Check if prediction is already ready
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # Find if a prediction is READY and the release time has passed
                cursor.execute(
                    "SELECT prediction_type, prediction_release_time FROM payment_requests "
                    "WHERE user_id = %s AND status = 'PREDICTION_READY' AND prediction_release_time <= NOW()",
                    (user_id,)
                )
                ready_request = cursor.fetchone()
                
                if ready_request:
                    # Prediction is ready, show it and update status
                    prediction_text = (
                        f"🔮 **Your {ready_request['prediction_type'].replace('_', ' ')} Prediction** 🔮\n\n"
                        "***Placeholder Prediction Content:***\n"
                        "The market trend for the next period is HIGH volatility with a strong upward bias. "
                        "Key resistance levels are X, Y, Z. Exercise caution at close."
                    )
                    
                    # Update status to 'CONSUMED' (or delete, depending on desired history)
                    cursor.execute(
                        "UPDATE payment_requests SET status = 'CONSUMED' WHERE user_id = %s AND status = 'PREDICTION_READY'", 
                        (user_id,)
                    )
                    conn.commit()
                    
                    await query.edit_message_text(
                        prediction_text,
                        reply_markup=get_main_keyboard(),
                        parse_mode='Markdown'
                    )
                    return ConversationHandler.END

                # Check if a payment is accepted but not yet released
                cursor.execute(
                    "SELECT prediction_type, prediction_release_time FROM payment_requests "
                    "WHERE user_id = %s AND status = 'ACCEPTED' AND prediction_release_time > NOW()",
                    (user_id,)
                )
                pending_request = cursor.fetchone()
                
                if pending_request:
                    # Prediction is accepted but not time yet
                    time_diff = pending_request['prediction_release_time'] - datetime.now()
                    hours, remainder = divmod(time_diff.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    await query.edit_message_text(
                        f"⏳ **Prediction Accepted!**\n"
                        f"Your {pending_request['prediction_type'].replace('_', ' ')} prediction will be available in:\n"
                        f"**{int(hours)} hours and {int(minutes)} minutes** (approx.)\n\n"
                        "Check back here later!",
                        reply_markup=get_main_keyboard(),
                        parse_mode='Markdown'
                    )
                    return ConversationHandler.END


            except Exception as e:
                logger.error(f"Error checking prediction status: {e}")
            finally:
                cursor.close()
                conn.close()

        # If no ready or accepted prediction, show tiers
        await query.edit_message_text(
            "Select a prediction plan:",
            reply_markup=get_prediction_options_keyboard(),
        )
        return PREDICTION_CHOICE # Move to prediction choice state

    elif data == "main_menu":
        await query.edit_message_text(
            "Welcome back! Choose an option below:",
            reply_markup=get_main_keyboard(),
        )
        return ConversationHandler.END

    return ConversationHandler.END

async def select_prediction_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles selection of a prediction plan and initiates the payment flow."""
    query = update.callback_query
    await query.answer()
    
    plan_key = query.data.split('_')[1]
    plan_info = PREDICTION_PLANS.get(plan_key)
    
    if not plan_info:
        await query.edit_message_text("Invalid plan selected. Please try again.", reply_markup=get_prediction_options_keyboard())
        return PREDICTION_CHOICE

    # Store plan info in user_data for later use
    context.user_data["plan_key"] = plan_key
    context.user_data["price"] = plan_info["price"]
    
    message_text = (
        f"You selected: **{plan_info['label']}**\n\n"
        f"1. Please send **{plan_info['price']}₹** to the payment ID below.\n"
        f"   UPI ID: `{PAYMENT_ID}`\n"
        f"2. After payment, click the **Sended 🟢** button.\n"
        "*(Image of QR/ID is attached below)*"
    )

    # Note: We simulate the attachment by sending a text message with the image URL,
    # as the Telegram API requires sending the image separately.
    await context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=PAYMENT_QR_URL,
        caption="Use this QR or UPI ID for payment."
    )

    await query.edit_message_text(
        message_text,
        reply_markup=get_sended_keyboard(),
        parse_mode='Markdown'
    )
    
    return PREDICTION_CHOICE

async def payment_sended(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the 'sended' button click and asks for UTR."""
    query = update.callback_query
    await query.answer()

    if "plan_key" not in context.user_data:
        await query.edit_message_text("Payment flow expired or restarted. Please select a plan again.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    await query.edit_message_text(
        "Please reply with the **12-digit UTR/Reference Number** of your payment to verify."
    )
    
    # Store the payment request in the database with PENDING_UTR status
    user = query.from_user
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Check for existing PENDING payments
            cursor.execute("DELETE FROM payment_requests WHERE user_id = %s AND status IN ('PENDING_UTR', 'PENDING_ADMIN')", (user.id,))
            
            sql = (
                "INSERT INTO payment_requests (user_id, chat_id, username, prediction_type, price, status) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            )
            val = (
                user.id,
                query.message.chat_id,
                user.username if user.username else str(user.id),
                context.user_data["plan_key"],
                context.user_data["price"],
                'PENDING_UTR'
            )
            cursor.execute(sql, val)
            conn.commit()
            context.user_data['db_request_id'] = cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting request: {e}")
            await context.bot.send_message(user.id, "An error occurred while saving your request. Please try again.")
            return ConversationHandler.END
        finally:
            cursor.close()
            conn.close()

    return AWAITING_UTR # Move to AWAITING_UTR state

# --- 6. MESSAGE HANDLERS (UTR Input) ---

async def handle_utr_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the UTR input from the user."""
    utr_number = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Simple validation (12 digits, can be improved)
    if not utr_number.isdigit() or len(utr_number) not in [10, 12]:
        await update.message.reply_text("❌ Invalid UTR. Please enter a 10 or 12-digit UTR/Reference number.")
        return AWAITING_UTR
    
    if 'db_request_id' not in context.user_data:
        await update.message.reply_text("Session expired. Please start the prediction process again from the main menu.")
        return ConversationHandler.END

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Update the request with UTR and change status to PENDING_ADMIN
            sql = (
                "UPDATE payment_requests SET utr_number = %s, status = 'PENDING_ADMIN' "
                "WHERE id = %s AND user_id = %s"
            )
            val = (utr_number, context.user_data['db_request_id'], user_id)
            cursor.execute(sql, val)
            conn.commit()
            
            # Send success message to user
            await update.message.reply_text(
                "✅ **Payment Verification Initiated!**\n\n"
                "We have received your UTR number. Your request is now pending review by the administrator. "
                "You will be notified once the payment is confirmed. This usually takes **1-2 hours**.",
                parse_mode='Markdown'
            )
            
            # Notify the Admin
            admin_id = get_admin_id_from_db()
            await context.bot.send_message(
                admin_id,
                f"🔔 New Payment Request PENDING ADMIN review! Use /admin to view. UTR: {utr_number}"
            )

        except Exception as e:
            logger.error(f"Error updating UTR: {e}")
            await update.message.reply_text("An internal error occurred. Please contact support.")
        finally:
            cursor.close()
            conn.close()
            
    # Clean up user data
    context.user_data.clear()
    return ConversationHandler.END

# --- 7. ADMIN CALLBACK HANDLERS ---

# Job function to run when the schedule time is reached
async def release_prediction(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to update the prediction status to READY and notify the user."""
    job = context.job
    user_id = job.data['user_id']
    chat_id = job.data['chat_id']
    prediction_type = job.data['prediction_type']
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Update status to PREDICTION_READY
            sql = "UPDATE payment_requests SET status = 'PREDICTION_READY' WHERE user_id = %s AND status = 'ACCEPTED' ORDER BY id DESC LIMIT 1"
            cursor.execute(sql, (user_id,))
            conn.commit()
            
            await context.bot.send_message(
                chat_id,
                f"🎉 **Prediction Ready!** 🎉\n\n"
                f"Your **{prediction_type.replace('_', ' ')}** prediction is now available! "
                "Click the '🔮 Prediction' button in the main menu to view it.",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error releasing prediction for user {user_id}: {e}")
        finally:
            cursor.close()
            conn.close()


async def admin_handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles admin Accept/Reject button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    admin_id = get_admin_id_from_db()
    if query.from_user.id != admin_id:
        await query.edit_message_text("🚫 You are not authorized to perform this action.")
        return
    
    action, request_id = data.split('_')[1], int(data.split('_')[2])
    
    conn = get_db_connection()
    if not conn:
        await query.edit_message_text("Database error. Cannot process request.")
        return

    cursor = conn.cursor(dictionary=True)
    try:
        if action == "reject":
            # Reject logic
            cursor.execute("UPDATE payment_requests SET status = 'REJECTED' WHERE id = %s", (request_id,))
            conn.commit()
            
            # Fetch user info to notify them
            cursor.execute("SELECT user_id, username FROM payment_requests WHERE id = %s", (request_id,))
            req = cursor.fetchone()

            await query.edit_message_text(f"❌ Request ID {request_id} rejected.", parse_mode='Markdown')
            if req:
                await context.bot.send_message(
                    req['user_id'],
                    "🚨 **Payment Failed!**\n\n"
                    "We could not verify your payment with the UTR provided. Please re-check the UTR and try the payment process again, or contact support.",
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
            
        elif action == "accept":
            # Start the time setting flow in admin's chat
            context.user_data['admin_request_id'] = request_id
            await query.edit_message_text(
                f"✅ **Request ID {request_id} accepted.**\n\n"
                "Now, reply with the **delay time in seconds** before the prediction should be released (e.g., `3600` for 1 hour, or `10` for testing)."
            )
            # Use ConversationHandler to capture the next admin message (delay time)
            return "AWAITING_DELAY_TIME"

    except Exception as e:
        logger.error(f"Error in admin_handle_action: {e}")
        await query.edit_message_text("An internal error occurred durin