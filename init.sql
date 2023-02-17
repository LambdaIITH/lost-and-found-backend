CREATE TABLE users (
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) PRIMARY KEY,
  phone_number NUMERIC(10) NOT NULL,
);

CREATE TABLE lost (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(255) NOT NULL,
  user_email VARCHAR(255) NOT NULL,
  date_of_posting TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status BOOLEAN NOT NULL DEFAULT FALSE, -- false = not found yet, true = found
  FOREIGN KEY (user_email) REFERENCES users(email),
);

