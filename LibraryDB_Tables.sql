-- Create the LibraryDB database
CREATE DATABASE LibraryDB;
GO

-- Use the LibraryDB
USE LibraryDB;
GO

-- Users Table
CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(150) NOT NULL,
    username NVARCHAR(50) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL
);
GO

-- Students Table
CREATE TABLE Students (
    student_id NVARCHAR(20) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    batch NVARCHAR(20),
    course NVARCHAR(50),
    dob DATE,
    gender NVARCHAR(10),
    email NVARCHAR(150),
    phone NVARCHAR(15)
);
GO

-- Staff Table
CREATE TABLE Staff (
    staff_register NVARCHAR(20) PRIMARY KEY,
    staff_name NVARCHAR(100) NOT NULL,
    designation NVARCHAR(100),
    department NVARCHAR(100),
    course NVARCHAR(100),
    date_of_birth DATE,
    gender NVARCHAR(10),
    email NVARCHAR(150),
    phone_number NVARCHAR(15)
);
GO

-- Books Table
CREATE TABLE Books (
    book_id NVARCHAR(20) PRIMARY KEY,
    book_name NVARCHAR(150) NOT NULL,
    author_name NVARCHAR(100) NOT NULL,
    publisher NVARCHAR(100),
    edition NVARCHAR(50),
    publishing_year INT,
    purchase_date DATE
);
GO

-- IssuedBooks Table (Student Issues)
CREATE TABLE IssuedBooks (
    issue_id INT IDENTITY(1,1) PRIMARY KEY,
    book_id NVARCHAR(20) FOREIGN KEY REFERENCES Books(book_id),
    student_id NVARCHAR(20) FOREIGN KEY REFERENCES Students(student_id),
    issue_date DATE NOT NULL,
    return_date DATE,
    renew_count INT DEFAULT 0,
    due_date DATE,
    fine_amount FLOAT DEFAULT 0.0
);
GO

-- Return_book Table (Student Returns)
CREATE TABLE Return_book (
    return_id INT IDENTITY(1,1) PRIMARY KEY,
    issue_id INT FOREIGN KEY REFERENCES IssuedBooks(issue_id),
    student_id NVARCHAR(20) FOREIGN KEY REFERENCES Students(student_id),
    book_id NVARCHAR(20) FOREIGN KEY REFERENCES Books(book_id),
    issue_date DATE,
    return_date DATE,
    renew_count INT,
    due_date DATE,
    fine_amount FLOAT
);
GO

-- Staff_IssuedBooks Table
CREATE TABLE Staff_IssuedBooks (
    issue_id INT IDENTITY(1,1) PRIMARY KEY,
    book_id NVARCHAR(20) FOREIGN KEY REFERENCES Books(book_id),
    staff_register NVARCHAR(20) FOREIGN KEY REFERENCES Staff(staff_register),
    issue_date DATE NOT NULL,
    return_date DATE,
    renew_count INT DEFAULT 0,
    due_date DATE,
    fine_amount FLOAT DEFAULT 0.0
);
GO

-- Staff_Return_book Table
CREATE TABLE Staff_Return_book (
    return_id INT IDENTITY(1,1) PRIMARY KEY,
    issue_id INT FOREIGN KEY REFERENCES Staff_IssuedBooks(issue_id),
    staff_register NVARCHAR(20) FOREIGN KEY REFERENCES Staff(staff_register),
    book_id NVARCHAR(20) FOREIGN KEY REFERENCES Books(book_id),
    issue_date DATE,
    return_date DATE,
    renew_count INT,
    due_date DATE,
    fine_amount FLOAT
);
GO
