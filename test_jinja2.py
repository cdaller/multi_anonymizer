from faker import Faker
from jinja2 import Template

def _get_faker_methods():
    """Fetch all available Faker methods, filtering out internal methods."""
    faker_methods = {}
    for method in dir(fake):
        if not method.startswith("_"):
            try:
                attr = getattr(fake, method)
                if callable(attr):
                    faker_methods[method] = attr
            except TypeError:
                continue
    return faker_methods


def faker_proxy():
    """Return a dictionary of Faker functions that can be used in Jinja2 templates."""
    return {method: (lambda *args, m=method, **kwargs: faker_methods[m](*args, **kwargs)) for method in faker_methods}

# Initialize Faker and generate fake data
fake = Faker()

faker_methods = _get_faker_methods()

# Define a Jinja2 template that uses the fake data
template_str = "Hello, {{ faker.name() }}! Random Int: {{ faker.random_int(100000, 200000) }}"
template = Template(template_str)

# Render the template with fake data
result = template.render(faker=faker_proxy())

print(result)