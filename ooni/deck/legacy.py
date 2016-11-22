class NotAnOption(Exception):
    pass

def subargs_to_options(subargs):
    options = {}

    def parse_option_name(arg):
        if arg.startswith("--"):
            return arg[2:]
        elif arg.startswith("-"):
            return arg[1:]
        raise NotAnOption

    subargs = iter(reversed(subargs))
    for subarg in subargs:
        try:
            value = subarg
            name = parse_option_name(subarg)
            options[name] = True
        except NotAnOption:
            try:
                name = parse_option_name(subargs.next())
                options[name] = value
            except StopIteration:
                break

    return options

def convert_legacy_deck(deck_data):
    """
    I take a legacy deck list and convert it to the new deck format.

    :param deck_data: in the legacy format
    :return: deck_data in the new format
    """
    assert isinstance(deck_data, list), "Legacy decks are lists"
    new_deck_data = {}
    new_deck_data["name"] = "Legacy deck"
    new_deck_data["description"] = "This is a legacy deck converted to the " \
                                   "new format"
    new_deck_data["bouncer"] = None
    new_deck_data["tasks"] = []
    for deck_item in deck_data:
        deck_task = {"ooni": {}}

        options = deck_item["options"]
        deck_task["ooni"]["test_name"] = options.pop("test_file")
        deck_task["ooni"]["annotations"] = options.pop("annotations", {})
        deck_task["ooni"]["collector"] = options.pop("collector", None)

        # XXX here we end up picking only the last not none bouncer_address
        bouncer_address = options.pop("bouncer", None)
        if bouncer_address is not None:
            new_deck_data["bouncer"] = bouncer_address

        subargs = options.pop("subargs", [])
        for name, value in subargs_to_options(subargs).items():
            deck_task["ooni"][name] = value

        for name, value in options.items():
            deck_task["ooni"][name] = value

        new_deck_data["tasks"].append(deck_task)

    return new_deck_data
