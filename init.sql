-- name: create_schema#
-- create the schema for the lost and found app
CREATE TABLE users (
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) PRIMARY KEY,
  phone_number NUMERIC(10) NOT NULL
);

CREATE TABLE lost (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(255) NOT NULL,
  user_email VARCHAR(255) NOT NULL,
  date_of_posting TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status BOOLEAN NOT NULL DEFAULT FALSE, -- false = not found yet, true = found
  FOREIGN KEY (user_email) REFERENCES users(email)
);

--name: insert_item!
-- insert a new item into the lost table
INSERT INTO lost (name, description, user_email) VALUES (:name, :description, :user_email);

--name: get_all_items
-- get all items from the lost table which are still not found
SELECT * FROM lost where status = false order by date_of_posting desc;

--name: update_item!
-- update the status of an item to found
UPDATE lost SET status = true where id = :id;

--name: get_email
-- get the email of the user given the lost item id
SELECT user_email FROM lost where id = :id;

--name: add_user!
-- add a new user to the users table
INSERT INTO users (name, email, phone_number) VALUES (:name, :email, :phone_number);