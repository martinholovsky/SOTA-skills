from string import Template


def render(user_template, name):
    return Template(user_template).safe_substitute(name=name)
