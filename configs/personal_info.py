from addict import Dict
from configs.google_accounts import account_info

personal_info = Dict(
    name = "John Titor",
    email = account_info.main_google_account.email,
    # phone = "+1 647 600 0000",
    # address = "123 Main St, Anytown, USA",
    # city = "Anytown",
    # state = "CA",
    # zip = "12345",
    icml25_paper_title = "Ipsum Lorem is all you need",
    icml25_paper_url = "https://openreview.net/forum?id=IpSum6loRem",
)