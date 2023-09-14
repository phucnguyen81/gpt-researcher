""" Utility functions """


def get_attr(obj, attrs):
    """ Get a nested attribute from an object given the attribute chain
    For example, to get the text from an OpenAI chat completion response:
    text = get_attr(response , ["choices", 0, "message", "content"])
    """
    for attr in attrs:
        if obj is None:
            break
        if isinstance(obj, dict):
            obj = obj.get(attr, None)
        elif isinstance(obj, list):
            idx = int(attr)
            obj = obj[idx] if idx < len(obj) else None
        else:
            obj = getattr(obj, attr, None)
    return obj
