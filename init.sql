CREATE TABLE users ( 
  name VARCHAR(255) NOT NULL, -- name of the user
  email VARCHAR(255) PRIMARY KEY, -- email of the user
  phone_number NUMERIC(10) NOT NULL UNIQUE -- phone number of the user
);

CREATE TABLE lost (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL, -- name of the item lost
  description VARCHAR(255) NOT NULL,
  user_email VARCHAR(255) NOT NULL, -- email of the user who lost the item
  date_of_posting TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status BOOLEAN NOT NULL DEFAULT FALSE, -- false = not found yet, true = found
  FOREIGN KEY (user_email) REFERENCES users(email)
);