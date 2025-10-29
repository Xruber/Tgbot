-- -----------------------------------------------------------------------------
-- Optimized Schema for Telegram Bot Database
-- This script ensures tables exist and uses efficient data types/indexes.
-- -----------------------------------------------------------------------------

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS sql12805009;

-- Use the database
USE sql12805009;

-- Table to store user payments and prediction requests
CREATE TABLE IF NOT EXISTS payment_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL COMMENT 'Numerical Telegram User ID (Required for bot functions)',
    chat_id BIGINT NOT NULL COMMENT 'The chat ID where the request originated (often same as user_id)',
    username VARCHAR(255) COMMENT 'Telegram @username (nullable)',
    prediction_type VARCHAR(50) NOT NULL COMMENT 'e.g., 1_hour, 7_day',
    price DECIMAL(10, 2) NOT NULL,
    utr_number VARCHAR(100) UNIQUE COMMENT 'Unique Transaction Reference for payment verification',

    -- Use ENUM for status for improved performance and data integrity.
    status ENUM('PENDING_UTR', 'PENDING_ADMIN', 'ACCEPTED', 'PREDICTION_READY', 'REJECTED') NOT NULL DEFAULT 'PENDING_UTR',

    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_accepted_at DATETIME COMMENT 'Timestamp when admin approved the payment',
    prediction_release_time DATETIME COMMENT 'The scheduled time when the prediction is available',

    -- Indexes for faster lookups based on user or status
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);

-- Table to store the main admin ID and other bot settings
CREATE TABLE IF NOT EXISTS bot_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL COMMENT 'Value of the setting (e.g., a numerical ID or a string)',
    
    -- Add an index for fetching by key, although the PRIMARY KEY handles this well
    INDEX idx_setting_key (setting_key)
);

-- Insert the admin user ID for initial setup.
-- IMPORTANT: Telegram bots use numerical IDs (BIGINT), not the @username string.
-- You must REPLACE '123456789' with your actual NUMERICAL Telegram User ID.
-- We use INSERT IGNORE to prevent an error if this row already exists.
INSERT IGNORE INTO bot_settings (setting_key, setting_value)
VALUES ('ADMIN_ID', '6239774927');
