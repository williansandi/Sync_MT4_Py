def digital_underlying_list(api, message):
    if message["name"] == "digital-option-instruments.underlying-list":
        api.underlying_list_data = message["msg"]