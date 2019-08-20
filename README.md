# forwarn2_build
ForWarn 2 product build scripts

Note: the directories `ForWarn2` and `ForWarn2_Sqrt` mirror the directory structure of the final resting place of generated products. They are used for testing purposes only! Do not put products here for production sites!

Setup:

- Make a text file called `todo_product_days`. This file contains a list of julian days (see `all_product_days`) that still need products. An automated run of `make_products` with no `-d` argument will automatically write a new `todo_product_days` file and remove days that were completed successfully.

- Make another text file called `mail_to_addrs.txt`. This file contains a list of email addresses that the system will send logs to. (Use the `--no-email` flag to suppress this function.


