### Order Placement Automation for Italist

check if theres files on the FTP
if yes: download files
if no: quit

open downloaded files, group orders by PO and set up batch, archive files on FTP
for each batch:
- log into italist site
- use sku id to lookup product URL from products db
- open URL with selenium
- add each line item sku to cart
- pay for item
- reset browser session

archive order files locally
send summary e-mail

we'll also need to figure out order tracking separately

DOWNLOAD TRACKING URL:
GMT 0, GMT 6, GMT 12, GMT 18
https://flip-orders.s3.us-west-2.amazonaws.com/flip_orders.csv