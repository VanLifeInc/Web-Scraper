INSERT INTO kijiji_ads (title, price, location, description, ad_id, image_loc, url, date_posted, branch,last_updated)
VALUES
('1', '2', '3', '4', '5', '6', '7', NULL, '9','2018-07-29')
ON CONFLICT (ad_id)
DO
UPDATE
SET title = EXCLUDED.title,
price = EXCLUDED.price,
description = EXCLUDED.description,
last_updated = EXCLUDED.last_updated;

