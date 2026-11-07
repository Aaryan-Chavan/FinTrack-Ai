CREATE DATABASE finance_db;
USE finance_db;

CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    password VARCHAR(100)
);

CREATE TABLE Transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    category VARCHAR(100),
    amount DECIMAL(10,2),
    type VARCHAR(50),
    date DATE,
    UNIQUE(category, amount, type, date),
    FOREIGN KEY (user_id) REFERENCES Users(id)
);

SELECT*FROM Users;
SELECT*FROM Transactions;