from faker import Faker

def _get_faker_methods(fake):
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

def main():
    Faker.seed(0)  # Set a seed for reproducibility
    fake = Faker()
    # Get all available methods from the Faker instance
    faker_methods = _get_faker_methods(fake)

    for method in faker_methods:
        try:
            # Call the method and print its name and an example value
            try:
                if method in ["binary", "get_providers", "image", "items", "tar", "xml", "zip"] or method.startswith("py"):
                    example_value = "<skipped>"
                else:
                    value_method = getattr(fake.unique, method, None)
                    example_value = value_method()
            except TypeError:
                example_value = "N/A"
            print(f"{method}: {example_value}")
        except TypeError:
            # Skip methods that require arguments
            print(f"{method}: Skipped (requires arguments)")

if __name__ == "__main__":
    main()