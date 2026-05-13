from faker import Faker
from collections import Counter

# Initialize Faker
fake = Faker()

# Generate 20,000 fake email addresses
# Use Faker's unique attribute for generating unique values
email_addresses = [fake.unique.ascii_company_email() for _ in range(20000)]

# Check for duplicates

email_counts = Counter(email_addresses)
duplicates = [email for email, count in email_counts.items() if count > 1]

# Output results
if duplicates:
    print(f"Found {len(duplicates)} duplicate email addresses:")
    print("\n".join(duplicates))
else:
    print("No duplicate email addresses found.")