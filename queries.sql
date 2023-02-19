-- get an item by ID
-- :item_id is a parameter that will be passed to the query
-- the result is a single row with the columns from the "lost" table
-- or null if the item is not found

-- name: get_item_by_id
SELECT * FROM lost WHERE id = :item_id;


-- update the status of an item by ID
-- :item_id is a parameter that will be passed to the query
-- :new_status is a parameter that represents the new status of the item
-- it updates the "status" column of the "lost" table for the row with the given ID

-- name: update_item_status!
UPDATE lost SET status = :status WHERE id = :item_id;


-- name: get_all_items
SELECT * FROM lost;

-- name: create_item!
insert into lost (name, description, user_email) values (:name, :description, :user_email);
Footer