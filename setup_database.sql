-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS sql12805009;

-- Use the newly created database
USE sql12805009;

-- Table to store user payments and prediction requests
CREATE TABLE payment_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username VARCHAR(255),
    prediction_type VARCHAR(50) NOT NULL, -- e.g., '1_hour', '7_day'
    price DECIMAL(10, 2) NOT NULL,
    utr_number VARCHAR(100),
    status VARCHAR(50) NOT NULL, -- e.g., 'PENDING_UTR', 'PENDING_ADMIN', 'ACCEPTED', 'PREDICTION_READY'
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    admin_accepted_at DATETIME,
    prediction_release_time DATETIME -- The scheduled time when the prediction becomes available
);

-- Table to store the main admin ID
CREATE TABLE bot_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value VARCHAR(255)
);

-- Insert the admin user ID (REPLACE 123456789 WITH YOUR ACTUAL TELEGRAM USER ID)
INSERT INTO bot_settings (setting_key, setting_value) VALUES ('ADMIN_ID', '6239774927');

